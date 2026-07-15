"""Endpoint tests for transactional document uploads."""

from collections.abc import Iterator
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from uuid import UUID

import pytest
import backend.app.api.documents as documents_api_module
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from sqlalchemy import Engine, create_engine, event, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.api.documents import require_database_session
from backend.app.core.config import (
    ChunkingSettings,
    DocumentSettings,
    get_chunking_settings,
    get_document_settings,
)
from backend.app.core.database import Base
from backend.app.main import app
from backend.app.models.chunk import Chunk
from backend.app.models.document import Document
from backend.app.services.document_storage import build_upload_paths
from backend.app.services.text_splitter import TextSplittingError
from backend.tests.pdf_fixtures import build_text_pdf


@dataclass(slots=True)
class DocumentApiContext:
    """Isolated API client, settings, and in-memory database."""

    client: TestClient
    settings: DocumentSettings
    session_factory: sessionmaker[Session]
    engine: Engine


def build_encrypted_pdf() -> bytes:
    """Return a minimal password-protected PDF for HTTP contract testing."""
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.encrypt("secret")
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


@pytest.fixture
def document_api(tmp_path: Path) -> Iterator[DocumentApiContext]:
    """Provide the real endpoint with isolated files and SQLite persistence."""
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    settings = DocumentSettings(
        _env_file=None,
        upload_dir=tmp_path / "uploads",
        max_upload_size=20 * 1024 * 1024,
        max_pdf_pages=500,
        read_chunk_size=1024,
    )
    chunking = ChunkingSettings(
        _env_file=None,
        chunk_size=500,
        chunk_overlap=100,
        chunk_encoding_name="o200k_base",
    )

    def override_session() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[require_database_session] = override_session
    app.dependency_overrides[get_document_settings] = lambda: settings
    app.dependency_overrides[get_chunking_settings] = lambda: chunking
    try:
        with TestClient(app) as client:
            yield DocumentApiContext(client, settings, session_factory, engine)
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_upload_pdf_returns_201_and_preserves_page_boundaries(
    document_api: DocumentApiContext,
) -> None:
    """A valid PDF is stored under its UUID and persisted with form feeds."""
    pdf = build_text_pdf(["first", "", "third"])

    response = document_api.client.post(
        "/documents/upload",
        files={"file": ("Example.PDF", pdf, "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "filename", "size", "status", "created_at"}
    assert body["filename"] == "Example.PDF"
    assert body["size"] == len(pdf)
    assert body["status"] == "ready"
    document_id = UUID(body["id"])

    with document_api.session_factory() as session:
        document = session.scalar(select(Document).where(Document.id == document_id))
        chunks = session.scalars(
            select(Chunk)
            .where(Chunk.doc_id == document_id)
            .order_by(Chunk.chunk_index)
        ).all()
    assert document is not None
    assert document.extracted_text.count("\f") == 2
    assert "first" in document.extracted_text
    assert "third" in document.extracted_text
    assert [chunk.page for chunk in chunks] == [1, 3]
    assert [chunk.chunk_index for chunk in chunks] == [0, 1]
    assert all(chunk.chunk_metadata["encoding_name"] == "o200k_base" for chunk in chunks)

    paths = build_upload_paths(document_api.settings.upload_dir, document_id, ".pdf")
    assert paths.final.read_bytes() == pdf
    assert not paths.part.exists()


def test_upload_utf8_bom_text_succeeds(document_api: DocumentApiContext) -> None:
    """TXT is treated as page one and its UTF-8 BOM is removed."""
    response = document_api.client.post(
        "/documents/upload",
        files={"file": ("notes.txt", b"\xef\xbb\xbfhello", "text/plain")},
    )

    assert response.status_code == 201
    document_id = UUID(response.json()["id"])
    with document_api.session_factory() as session:
        document = session.get(Document, document_id)
        chunks = session.scalars(
            select(Chunk).where(Chunk.doc_id == document_id)
        ).all()
    assert document is not None
    assert document.extracted_text == "hello"
    assert len(chunks) == 1
    assert chunks[0].page == 1


def test_upload_requires_file_field(document_api: DocumentApiContext) -> None:
    """FastAPI retains its standard validation response for a missing file."""
    response = document_api.client.post("/documents/upload")

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("filename", "content", "content_type", "expected_detail"),
    [
        ("empty.txt", b"", "text/plain", "The uploaded file is empty."),
        (
            "legacy.txt",
            b"\xff\xfeinvalid",
            "text/plain",
            "Text documents must use UTF-8 encoding.",
        ),
        (
            "damaged.pdf",
            b"%PDF-1.7\ninvalid",
            "application/pdf",
            "The uploaded PDF is invalid or damaged.",
        ),
        (
            "blank.pdf",
            build_text_pdf(["", ""]),
            "application/pdf",
            "The uploaded document contains no extractable text.",
        ),
        (
            "encrypted.pdf",
            build_encrypted_pdf(),
            "application/pdf",
            "Encrypted PDF files are not supported.",
        ),
    ],
)
def test_bad_documents_return_400_and_leave_no_files(
    document_api: DocumentApiContext,
    filename: str,
    content: bytes,
    content_type: str,
    expected_detail: str,
) -> None:
    """Client content failures do not leave rows or upload artifacts."""
    response = document_api.client.post(
        "/documents/upload",
        files={"file": (filename, content, content_type)},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": expected_detail}
    assert list(document_api.settings.upload_dir.glob("*")) == []
    with document_api.session_factory() as session:
        assert session.scalar(select(Document)) is None
        assert session.scalar(select(Chunk)) is None


def test_unsupported_extension_returns_415(document_api: DocumentApiContext) -> None:
    """Files outside the Day 4 allowlist are rejected before persistence."""
    response = document_api.client.post(
        "/documents/upload",
        files={"file": ("image.png", b"not-an-image", "image/png")},
    )

    assert response.status_code == 415
    assert response.json() == {"detail": "The uploaded file type is not supported."}


def test_actual_size_limit_returns_413_and_cleans_part(
    document_api: DocumentApiContext,
) -> None:
    """The endpoint reports its configured limit and removes partial data."""
    document_api.settings.max_upload_size = 4
    response = document_api.client.post(
        "/documents/upload",
        files={"file": ("large.txt", b"12345", "text/plain")},
    )

    assert response.status_code == 413
    assert response.json() == {
        "detail": "The uploaded file exceeds the 4 bytes limit."
    }
    assert list(document_api.settings.upload_dir.glob("*")) == []


def test_split_failure_returns_500_and_leaves_no_rows_or_files(
    document_api: DocumentApiContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A tokenizer failure is safely mapped and rolls back all side effects."""

    def fail_split(*args: object, **kwargs: object) -> list[object]:
        del args, kwargs
        raise TextSplittingError("internal tokenizer failure")

    monkeypatch.setattr(documents_api_module, "split_pages", fail_split)
    response = document_api.client.post(
        "/documents/upload",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "The document could not be stored."}
    assert list(document_api.settings.upload_dir.glob("*")) == []
    with document_api.session_factory() as session:
        assert session.scalar(select(Document)) is None
        assert session.scalar(select(Chunk)) is None


def test_postgres_unavailable_returns_503_and_removes_promoted_file(
    document_api: DocumentApiContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed flush rolls back and removes the temporary file."""

    def fail_flush(self: Session, *args: object, **kwargs: object) -> None:
        del self, args, kwargs
        raise OperationalError("INSERT", {}, Exception("offline"))

    monkeypatch.setattr(Session, "flush", fail_flush)
    response = document_api.client.post(
        "/documents/upload",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    monkeypatch.undo()

    assert response.status_code == 503
    assert response.json() == {"detail": "The document database is unavailable."}
    assert list(document_api.settings.upload_dir.glob("*")) == []
    with document_api.session_factory() as session:
        assert session.scalar(select(Document)) is None
        assert session.scalar(select(Chunk)) is None


def test_chunk_flush_failure_rolls_back_document_and_cleans_file(
    document_api: DocumentApiContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A second-flush failure cannot leave a document without chunks."""
    original_flush = Session.flush
    flush_count = 0

    def fail_second_flush(
        self: Session,
        *args: object,
        **kwargs: object,
    ) -> None:
        nonlocal flush_count
        flush_count += 1
        if flush_count == 2:
            raise OperationalError("INSERT", {}, Exception("offline"))
        original_flush(self, *args, **kwargs)

    monkeypatch.setattr(Session, "flush", fail_second_flush)
    response = document_api.client.post(
        "/documents/upload",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    monkeypatch.undo()

    assert response.status_code == 503
    assert response.json() == {"detail": "The document database is unavailable."}
    assert list(document_api.settings.upload_dir.glob("*")) == []
    with document_api.session_factory() as session:
        assert session.scalar(select(Document)) is None
        assert session.scalar(select(Chunk)) is None


def test_commit_failure_after_promote_removes_final_file(
    document_api: DocumentApiContext,
) -> None:
    """A commit failure after os.replace removes the already promoted file."""

    def fail_commit(session: Session) -> None:
        del session
        raise OperationalError("COMMIT", {}, Exception("offline"))

    event.listen(Session, "before_commit", fail_commit)
    try:
        response = document_api.client.post(
            "/documents/upload",
            files={"file": ("notes.txt", b"hello", "text/plain")},
        )
    finally:
        event.remove(Session, "before_commit", fail_commit)

    assert response.status_code == 503
    assert response.json() == {"detail": "The document database is unavailable."}
    assert list(document_api.settings.upload_dir.glob("*")) == []
    with document_api.session_factory() as session:
        assert session.scalar(select(Document)) is None
        assert session.scalar(select(Chunk)) is None


def test_error_after_commit_keeps_file_for_committed_document(
    document_api: DocumentApiContext,
) -> None:
    """Cleanup must not orphan a row after the database commit succeeded."""

    def fail_after_commit(session: Session) -> None:
        del session
        raise OperationalError("COMMIT", {}, Exception("connection lost"))

    event.listen(Session, "after_commit", fail_after_commit)
    try:
        response = document_api.client.post(
            "/documents/upload",
            files={"file": ("notes.txt", b"hello", "text/plain")},
        )
    finally:
        event.remove(Session, "after_commit", fail_after_commit)

    assert response.status_code == 503
    with document_api.session_factory() as session:
        document = session.scalar(select(Document))
        chunk = session.scalar(select(Chunk))
    assert document is not None
    assert chunk is not None
    assert chunk.doc_id == document.id

    paths = build_upload_paths(
        document_api.settings.upload_dir,
        document.id,
        ".txt",
    )
    assert paths.final.read_bytes() == b"hello"


def test_pdf_page_limit_returns_400_and_cleans_file(
    document_api: DocumentApiContext,
) -> None:
    """PDF resource limits are reported without leaving upload artifacts."""
    document_api.settings.max_pdf_pages = 1
    response = document_api.client.post(
        "/documents/upload",
        files={
            "file": (
                "too-many-pages.pdf",
                build_text_pdf(["one", "two"]),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "The PDF exceeds the 1-page limit."}
    assert list(document_api.settings.upload_dir.glob("*")) == []


def test_unexpected_storage_error_returns_500(
    document_api: DocumentApiContext,
) -> None:
    """Filesystem implementation details are not returned to the client."""
    blocked_path = document_api.settings.upload_dir.parent / "blocked"
    blocked_path.write_text("not a directory", encoding="utf-8")
    document_api.settings.upload_dir = blocked_path

    response = document_api.client.post(
        "/documents/upload",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "The document could not be stored."}
