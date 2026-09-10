"""Unit tests for Day 10 BM25 tokenization, snapshots, and search."""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any
from uuid import UUID, uuid4

import pytest
from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.database import Base
from backend.app.core.logging import JSONL_LOG_MARKER
from backend.app.models.chunk import Chunk
from backend.app.models.document import Document
from backend.app.services.bm25 import (
    BM25_SEARCH_EVENT,
    BM25CorpusChunk,
    BM25IndexError,
    BM25Service,
    BM25Snapshot,
    BM25UnavailableError,
    build_bm25_snapshot,
    build_corpus_fingerprint,
    load_bm25_chunks,
    tokenize_bm25,
)


def corpus_chunk(
    *,
    content: str = "VPN 故障联系网络组，服务分机是 6203。",
    chunk_id: UUID | None = None,
    doc_id: UUID | None = None,
    chunk_index: int = 0,
    page: int = 1,
    filename: str = "policy.pdf",
    metadata: dict[str, Any] | None = None,
) -> BM25CorpusChunk:
    """Return one complete immutable corpus projection."""
    return BM25CorpusChunk(
        chunk_id=chunk_id or uuid4(),
        doc_id=doc_id or uuid4(),
        chunk_index=chunk_index,
        content=content,
        page=page,
        filename=filename,
        metadata={} if metadata is None else metadata,
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("报销", ["报", "销", "报销"]),
        ("VPN vpn ＶＰＮ", ["vpn", "vpn", "vpn"]),
        ("VPN-6203", ["vpn-6203", "vpn", "6203"]),
        ("ERR_AUTH_42", ["err_auth_42", "err", "auth", "42"]),
        ("版本 2026", ["版", "本", "版本", "2026"]),
        ("-- 😀 ！！！", []),
    ],
)
def test_tokenize_bm25_is_deterministic_for_mixed_text(
    text: str,
    expected: list[str],
) -> None:
    """Chinese, Latin, digits, and compound identifiers use one fixed rule."""
    assert tokenize_bm25(text) == expected


def test_corpus_fingerprint_is_canonical_and_covers_visible_fields() -> None:
    """Metadata key order is ignored while meaningful corpus changes are detected."""
    original = corpus_chunk(metadata={"b": 2, "a": 1})
    reordered = replace(original, metadata={"a": 1, "b": 2})
    baseline = build_corpus_fingerprint([original])

    assert build_corpus_fingerprint([reordered]) == baseline
    for changed in (
        replace(original, chunk_id=uuid4()),
        replace(original, doc_id=uuid4()),
        replace(original, chunk_index=1),
        replace(original, content="changed"),
        replace(original, page=2),
        replace(original, filename="changed.pdf"),
        replace(original, metadata={"a": 9}),
    ):
        assert build_corpus_fingerprint([changed]) != baseline


def test_empty_or_tokenless_corpus_does_not_build_an_index() -> None:
    """An empty searchable vocabulary stays a valid empty-result snapshot."""
    assert build_bm25_snapshot([]).index is None

    tokenless = corpus_chunk(content="！！！ 😀")
    snapshot = build_bm25_snapshot([tokenless])

    assert snapshot.index is None
    assert snapshot.tokenized_corpus == ((),)


def test_single_chunk_negative_score_match_is_not_dropped() -> None:
    """Token overlap, not score positivity, controls result inclusion."""
    chunk = corpus_chunk(content="vpn")
    service = BM25Service(lambda: (chunk,))

    results = service.search("VPN")

    assert [result.chunk_id for result in results] == [chunk.chunk_id]
    assert results[0].score <= 0.0


def test_no_token_overlap_returns_empty_instead_of_zero_score_fill() -> None:
    """BM25 never pads Top-K with unrelated corpus entries."""
    service = BM25Service(lambda: (corpus_chunk(content="采购审批"),))

    assert service.search("VPN 6203") == []


def test_doc_id_filter_runs_before_top_k() -> None:
    """A target-document match is not displaced by another document's rank."""
    first_doc = uuid4()
    second_doc = uuid4()
    dominant = corpus_chunk(
        content="VPN VPN VPN 6203",
        doc_id=first_doc,
        chunk_index=0,
    )
    target = corpus_chunk(
        content="VPN 使用说明",
        doc_id=second_doc,
        chunk_index=0,
    )
    service = BM25Service(lambda: (dominant, target))

    filtered = service.search("VPN 6203", top_k=1, doc_id=second_doc)

    assert [result.chunk_id for result in filtered] == [target.chunk_id]


def test_equal_scores_use_stable_identity_order() -> None:
    """Ties are deterministic across documents, positions, and Chunk UUIDs."""
    first_doc = UUID(int=1)
    second_doc = UUID(int=2)
    chunks = (
        corpus_chunk(
            content="vpn",
            chunk_id=UUID(int=4),
            doc_id=second_doc,
            chunk_index=0,
        ),
        corpus_chunk(
            content="vpn",
            chunk_id=UUID(int=3),
            doc_id=first_doc,
            chunk_index=1,
        ),
        corpus_chunk(
            content="vpn",
            chunk_id=UUID(int=2),
            doc_id=first_doc,
            chunk_index=0,
        ),
    )
    service = BM25Service(lambda: chunks)

    results = service.search("vpn", top_k=20)

    assert [result.chunk_id for result in results] == [
        UUID(int=2),
        UUID(int=3),
        UUID(int=4),
    ]


def test_unchanged_fingerprint_reuses_index_and_content_change_refreshes() -> None:
    """Repeated scans reuse the index while corpus changes replace it atomically."""
    chunks = [corpus_chunk(content="vpn 6203")]
    service = BM25Service(lambda: tuple(chunks))

    service.search("vpn")
    first_snapshot = service._snapshot
    service.search("vpn")
    assert service._snapshot is first_snapshot

    chunks[0] = replace(chunks[0], content="vpn 6203 changed")
    service.search("changed")

    assert service._snapshot is not first_snapshot
    assert service._snapshot is not None
    assert service._snapshot.fingerprint != first_snapshot.fingerprint


def test_refresh_failure_does_not_serve_a_stale_snapshot() -> None:
    """The current request fails closed even when an older snapshot exists."""
    fail = False
    chunk = corpus_chunk(content="vpn")

    def loader() -> tuple[BM25CorpusChunk, ...]:
        if fail:
            raise BM25UnavailableError("private database details")
        return (chunk,)

    service = BM25Service(loader)
    assert service.search("vpn")
    previous = service._snapshot
    fail = True

    with pytest.raises(BM25UnavailableError):
        service.search("vpn")

    assert service._snapshot is previous


class BrokenScoreIndex:
    """Return a controlled invalid score vector from the index boundary."""

    def __init__(self, scores: list[float]) -> None:
        self.scores = scores

    def get_scores(self, _: list[str]) -> list[float]:
        return self.scores


class RecordingIndex:
    """Capture the query token list passed to rank_bm25."""

    def __init__(self) -> None:
        self.query_tokens: list[str] = []

    def get_scores(self, query_tokens: list[str]) -> list[float]:
        self.query_tokens = query_tokens
        return [1.0]


@pytest.mark.parametrize("scores", [[], [float("nan")], [float("inf")]])
def test_invalid_score_results_fail_safely(scores: list[float]) -> None:
    """Wrong score counts and non-finite values never reach the API response."""
    chunk = corpus_chunk(content="vpn")
    fingerprint = build_corpus_fingerprint([chunk])
    service = BM25Service(lambda: (chunk,))
    service._snapshot = BM25Snapshot(
        fingerprint=fingerprint,
        chunks=(chunk,),
        tokenized_corpus=(("vpn",),),
        index=BrokenScoreIndex(scores),  # type: ignore[arg-type]
    )

    with pytest.raises(BM25IndexError):
        service.search("vpn")


def test_query_tokens_are_ordered_and_deduplicated_before_scoring() -> None:
    """Repeated query terms cannot multiply BM25 weights."""
    chunk = corpus_chunk(content="vpn 6203")
    fingerprint = build_corpus_fingerprint([chunk])
    recording = RecordingIndex()
    service = BM25Service(lambda: (chunk,))
    service._snapshot = BM25Snapshot(
        fingerprint=fingerprint,
        chunks=(chunk,),
        tokenized_corpus=(("vpn", "6203"),),
        index=recording,  # type: ignore[arg-type]
    )

    service.search("VPN vpn 6203 VPN")

    assert recording.query_tokens == ["vpn", "6203"]


@pytest.mark.parametrize(
    "metadata",
    [
        {"nested": {"private": "value"}},
        {"list": ["private"]},
        {"score": float("nan")},
    ],
)
def test_invalid_metadata_fails_before_index_build(metadata: dict[str, Any]) -> None:
    """Retrieval responses remain limited to finite JSON scalar metadata."""
    with pytest.raises(BM25IndexError):
        build_bm25_snapshot([corpus_chunk(metadata=metadata)])


def test_punctuation_query_is_empty_without_loading_postgres() -> None:
    """A tokenless query returns an empty result before corpus resolution."""
    called = False

    def loader() -> tuple[BM25CorpusChunk, ...]:
        nonlocal called
        called = True
        return ()

    service = BM25Service(loader)

    assert service.search("！！！😀") == []
    assert called is False


def test_safe_jsonl_log_excludes_query_tokens_content_and_metadata() -> None:
    """One successful search emits only the approved summary fields."""
    messages: list[tuple[str, dict[str, Any]]] = []
    handler_id = logger.add(
        lambda message: messages.append(
            (message.record["message"], message.record["extra"])
        ),
        level="INFO",
    )
    chunk = corpus_chunk(
        content="private-content VPN 6203",
        metadata={"secret": "private-metadata"},
    )
    try:
        BM25Service(lambda: (chunk,)).search("private-query VPN")
    finally:
        logger.remove(handler_id)

    events = [
        (json.loads(message), extra)
        for message, extra in messages
        if BM25_SEARCH_EVENT in message
    ]
    assert len(events) == 1
    event, extra = events[0]
    assert extra[JSONL_LOG_MARKER] is True
    assert event["event"] == BM25_SEARCH_EVENT
    assert event["query_token_count"] > 0
    assert event["corpus_size"] == 1
    raw = json.dumps(event, ensure_ascii=False)
    for forbidden in (
        "private-query",
        "private-content",
        "private-metadata",
        '"query_tokens"',
        '"content"',
        '"metadata"',
    ):
        assert forbidden not in raw


def test_load_bm25_chunks_reads_only_ready_documents_in_stable_order() -> None:
    """The loader projects joined rows and ignores non-ready documents."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    ready_id = UUID(int=2)
    ignored_id = UUID(int=1)
    with factory() as session:
        session.add_all(
            [
                Document(
                    id=ready_id,
                    filename="ready.pdf",
                    size=10,
                    status="ready",
                    extracted_text="ready",
                ),
                Document(
                    id=ignored_id,
                    filename="ignored.pdf",
                    size=10,
                    status="processing",
                    extracted_text="ignored",
                ),
            ]
        )
        session.flush()
        session.add_all(
            [
                Chunk(
                    chunk_id=UUID(int=12),
                    doc_id=ready_id,
                    chunk_index=1,
                    content="second",
                    page=2,
                    chunk_metadata={"b": 2},
                ),
                Chunk(
                    chunk_id=UUID(int=11),
                    doc_id=ready_id,
                    chunk_index=0,
                    content="first",
                    page=1,
                    chunk_metadata={"a": 1},
                ),
                Chunk(
                    chunk_id=UUID(int=10),
                    doc_id=ignored_id,
                    chunk_index=0,
                    content="ignored",
                    page=1,
                    chunk_metadata={},
                ),
            ]
        )
        session.commit()

    chunks = load_bm25_chunks(session_factory=factory)

    assert [chunk.chunk_id for chunk in chunks] == [UUID(int=11), UUID(int=12)]
    assert [chunk.filename for chunk in chunks] == ["ready.pdf", "ready.pdf"]
    engine.dispose()


@pytest.mark.parametrize("top_k", [0, 21, True, "5", 5.0, None])
def test_direct_service_rejects_invalid_top_k_before_loading(top_k: Any) -> None:
    """Direct callers cannot scan PostgreSQL with an invalid result limit."""
    called = False

    def loader() -> tuple[BM25CorpusChunk, ...]:
        nonlocal called
        called = True
        return ()

    with pytest.raises(ValueError):
        BM25Service(loader).search("vpn", top_k=top_k)

    assert called is False
