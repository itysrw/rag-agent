"""Tests for token-aware page splitting and Chunk persistence constraints."""

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import backend.app.services.text_splitter as text_splitter_module
from backend.app.core.config import ChunkingSettings
from backend.app.core.database import Base
from backend.app.models.chunk import Chunk
from backend.app.models.document import Document
from backend.app.services.document_parser import PageText
from backend.app.services.text_splitter import TextSplittingError, split_pages


def representative_text() -> str:
    """Return deterministic mixed Chinese, English, and Markdown-like prose."""
    sections = []
    for index in range(1, 31):
        sections.append(
            f"## 第 {index} 节\n"
            "企业知识库需要保留来源页码，并在切分时优先保持段落和句子边界。"
            "A deterministic tokenizer makes each experiment reproducible. "
            "列表项包括：上传校验、分页解析、事务写入；失败时执行补偿清理。"
        )
    return "\n\n".join(sections)


def test_chunking_settings_defaults_and_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Defaults are explicit and CHUNK_* variables override them directly."""
    for name in ("CHUNK_SIZE", "CHUNK_OVERLAP", "CHUNK_ENCODING_NAME"):
        monkeypatch.delenv(name, raising=False)
    defaults = ChunkingSettings(_env_file=None)
    assert defaults.chunk_size == 500
    assert defaults.chunk_overlap == 100
    assert defaults.chunk_encoding_name == "o200k_base"

    monkeypatch.setenv("CHUNK_SIZE", "300")
    monkeypatch.setenv("CHUNK_OVERLAP", "60")
    monkeypatch.setenv("CHUNK_ENCODING_NAME", " o200k_base ")
    overridden = ChunkingSettings(_env_file=None)
    assert overridden.chunk_size == 300
    assert overridden.chunk_overlap == 60
    assert overridden.chunk_encoding_name == "o200k_base"


@pytest.mark.parametrize(
    ("chunk_size", "chunk_overlap"),
    [(0, 0), (100, -1), (100, 100), (100, 101)],
)
def test_chunking_settings_reject_invalid_boundaries(
    chunk_size: int,
    chunk_overlap: int,
) -> None:
    """Invalid sizes and overlaps fail before a splitter is constructed."""
    with pytest.raises(ValidationError):
        ChunkingSettings(
            _env_file=None,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )


def test_chunking_settings_rejects_empty_encoding_name() -> None:
    """Whitespace cannot select a tokenizer encoding."""
    with pytest.raises(ValidationError):
        ChunkingSettings(_env_file=None, chunk_encoding_name="   ")


def test_split_pages_preserves_page_numbers_and_global_order() -> None:
    """Blank pages create no chunks and do not renumber later source pages."""
    pages = [
        PageText(page=1, text="第一页内容。" * 80),
        PageText(page=2, text=" \n "),
        PageText(page=3, text="Third-page content. " * 80),
    ]

    chunks = split_pages(
        pages,
        chunk_size=50,
        chunk_overlap=10,
        encoding_name="o200k_base",
    )

    assert {chunk.page for chunk in chunks} == {1, 3}
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    assert all(chunk.content.strip() for chunk in chunks)


@pytest.mark.parametrize(
    ("chunk_size", "chunk_overlap"),
    [(300, 60), (500, 100), (800, 160)],
)
def test_split_pages_respects_token_limit(
    chunk_size: int,
    chunk_overlap: int,
) -> None:
    """Every comparison configuration produces nonempty bounded chunks."""
    chunks = split_pages(
        [PageText(page=1, text=representative_text())],
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        encoding_name="o200k_base",
    )

    assert chunks
    assert all(chunk.content.strip() for chunk in chunks)
    assert all(chunk.metadata["token_count"] <= chunk_size for chunk in chunks)
    assert all(chunk.metadata["chunk_size"] == chunk_size for chunk in chunks)
    assert all(chunk.metadata["chunk_overlap"] == chunk_overlap for chunk in chunks)
    combined = "\n".join(chunk.content for chunk in chunks)
    assert all(f"第 {index} 节" in combined for index in range(1, 31))


def test_split_pages_is_deterministic_and_handles_special_token_text() -> None:
    """Repeated input, including special-token-like literals, is stable."""
    pages = [
        PageText(
            page=1,
            text=("literal <|endoftext|> marker should remain ordinary input. " * 60),
        )
    ]
    arguments = {
        "chunk_size": 100,
        "chunk_overlap": 20,
        "encoding_name": "o200k_base",
    }

    first = split_pages(pages, **arguments)
    second = split_pages(pages, **arguments)

    assert first == second
    assert any("<|endoftext|>" in chunk.content for chunk in first)


def test_separator_free_fallback_uses_bounded_tokenizer_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A long unbroken span must not invoke the tokenizer once per character."""

    class CountingEncoding:
        def __init__(self) -> None:
            self.calls = 0

        def encode(
            self,
            text: str,
            *,
            disallowed_special: object = (),
        ) -> list[int]:
            del disallowed_special
            self.calls += 1
            return list(range(len(text)))

    encoding = CountingEncoding()
    monkeypatch.setattr(
        text_splitter_module.tiktoken,
        "get_encoding",
        lambda _: encoding,
    )
    text = "".join(chr(0xE000 + index) for index in range(1_000))

    chunks = split_pages(
        [PageText(page=1, text=text)],
        chunk_size=100,
        chunk_overlap=20,
        encoding_name="counting",
    )

    assert chunks[0].content == text[:100]
    assert chunks[1].content == text[80:180]
    assert chunks[-1].content.endswith(text[-40:])
    assert encoding.calls < 100


def test_separator_free_fallback_preserves_unicode_text() -> None:
    """Token windows preserve Unicode boundaries, coverage, and forward progress."""
    text = "".join(chr(0x10000 + index) for index in range(200))

    chunks = split_pages(
        [PageText(page=1, text=text)],
        chunk_size=50,
        chunk_overlap=10,
        encoding_name="o200k_base",
    )

    positions = [text.index(chunk.content) for chunk in chunks]
    assert positions[0] == 0
    assert positions[-1] + len(chunks[-1].content) == len(text)
    assert all(left < right for left, right in zip(positions, positions[1:]))
    assert all(
        next_start <= start + len(chunk.content)
        for start, next_start, chunk in zip(positions, positions[1:], chunks)
    )
    assert all(chunk.metadata["token_count"] <= 50 for chunk in chunks)
    assert all("\ufffd" not in chunk.content for chunk in chunks)


def test_split_pages_rejects_unknown_encoding_and_blank_input() -> None:
    """Tokenizer lookup and empty output failures use the safe service error."""
    with pytest.raises(TextSplittingError):
        split_pages(
            [PageText(page=1, text="hello")],
            chunk_size=100,
            chunk_overlap=20,
            encoding_name="not-a-real-encoding",
        )

    with pytest.raises(TextSplittingError):
        split_pages(
            [PageText(page=1, text=" \n ")],
            chunk_size=100,
            chunk_overlap=20,
            encoding_name="o200k_base",
        )


def test_chunk_unique_order_and_json_metadata() -> None:
    """Chunk order is unique per document and metadata is JSON serializable."""
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    try:
        with Session(engine) as session:
            document = Document(
                filename="notes.txt",
                size=5,
                status="ready",
                extracted_text="hello",
            )
            session.add(document)
            session.flush()
            session.add(
                Chunk(
                    doc_id=document.id,
                    chunk_index=0,
                    content="hello",
                    page=1,
                    chunk_metadata={
                        "chunk_size": 500,
                        "chunk_overlap": 100,
                        "length_unit": "token",
                        "encoding_name": "o200k_base",
                        "token_count": 1,
                    },
                )
            )
            session.commit()

            stored = session.query(Chunk).one()
            assert stored.chunk_metadata["token_count"] == 1

            session.add(
                Chunk(
                    doc_id=document.id,
                    chunk_index=0,
                    content="duplicate",
                    page=1,
                    chunk_metadata={"token_count": 1},
                )
            )
            with pytest.raises(IntegrityError):
                session.commit()
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
