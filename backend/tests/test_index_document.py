"""Tests for explicit Qdrant initialization and document indexing commands."""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.app.commands.index_document import (
    DocumentChunksNotFoundError,
    DocumentNotFoundError,
    index_document,
    print_summary,
)
from backend.app.commands.init_qdrant import initialize_qdrant
from backend.app.core.config import QdrantSettings
from backend.app.core.database import Base
from backend.app.models.chunk import Chunk
from backend.app.models.document import Document
from backend.app.services.qdrant_store import VectorizedChunk


def basis_vector(position: int) -> tuple[float, ...]:
    """Return one normalized vector with a deterministic position."""
    values = [0.0] * 512
    values[position] = 1.0
    return tuple(values)


class StubEmbeddingClient:
    """Record ordered passage batches and return deterministic vectors."""

    dimension = 512

    def __init__(self) -> None:
        self.texts: list[str] = []

    def embed_documents(self, texts: list[str]) -> list[tuple[float, ...]]:
        self.texts.extend(texts)
        return [basis_vector(index) for index, _ in enumerate(texts)]


class StubVectorStore:
    """Record initialization and complete in-memory point inputs."""

    def __init__(self, *, on_initialize: Any | None = None) -> None:
        self.settings = QdrantSettings(_env_file=None, collection="test-documents")
        self.on_initialize = on_initialize
        self.initialized = False
        self.chunks: list[VectorizedChunk] = []

    def initialize_collection(self) -> None:
        if self.on_initialize is not None:
            self.on_initialize()
        self.initialized = True

    def upsert_chunks(self, chunks: list[VectorizedChunk]) -> int:
        assert self.initialized is True
        self.chunks.extend(chunks)
        return len(chunks)


class TrackingSession(Session):
    """Expose whether the context closed PostgreSQL before external work."""

    was_closed = False

    def close(self) -> None:
        self.was_closed = True
        super().close()


@pytest.fixture
def indexed_document_database() -> tuple[Any, UUID, list[TrackingSession]]:
    """Provide a document with out-of-order inserted Chunks in SQLite."""
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    document_id = uuid4()
    with Session(bind=engine) as session:
        with session.begin():
            session.add(
                Document(
                    id=document_id,
                    filename="policy.pdf",
                    size=12,
                    status="ready",
                    extracted_text="zero one",
                )
            )
            session.flush()
            session.add_all(
                [
                    Chunk(
                        chunk_id=uuid4(),
                        doc_id=document_id,
                        chunk_index=1,
                        content="one",
                        page=2,
                        chunk_metadata={"token_count": 1},
                    ),
                    Chunk(
                        chunk_id=uuid4(),
                        doc_id=document_id,
                        chunk_index=0,
                        content="zero",
                        page=1,
                        chunk_metadata={"token_count": 1},
                    ),
                ]
            )

    sessions: list[TrackingSession] = []

    def factory() -> TrackingSession:
        session = TrackingSession(bind=engine, expire_on_commit=False)
        sessions.append(session)
        return session

    try:
        yield factory, document_id, sessions
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_index_document_closes_database_before_embedding_and_qdrant(
    indexed_document_database: tuple[Any, UUID, list[TrackingSession]],
) -> None:
    """The command maps ordered rows only after its read session closes."""
    session_factory, document_id, sessions = indexed_document_database
    embedding = StubEmbeddingClient()

    def assert_database_closed() -> None:
        assert sessions[-1].was_closed is True

    store = StubVectorStore(on_initialize=assert_database_closed)

    summary = index_document(
        document_id,
        session_factory=session_factory,
        embedding_client_factory=lambda: embedding,  # type: ignore[arg-type]
        vector_store_factory=lambda: store,  # type: ignore[arg-type]
    )

    assert embedding.texts == ["zero", "one"]
    assert [chunk.chunk_index for chunk in store.chunks] == [0, 1]
    assert [chunk.page for chunk in store.chunks] == [1, 2]
    assert all(chunk.filename == "policy.pdf" for chunk in store.chunks)
    assert store.chunks[0].vector[0] == 1.0
    assert store.chunks[1].vector[1] == 1.0
    assert summary.document_id == document_id
    assert summary.collection == "test-documents"
    assert summary.chunk_count == 2

    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Chunk)) == 2


def test_index_document_missing_rows_fail_before_external_clients(
    indexed_document_database: tuple[Any, UUID, list[TrackingSession]],
) -> None:
    """Unknown Documents do not initialize Qdrant or load BGE."""
    session_factory, _, _ = indexed_document_database
    external_called = False

    def fail_if_called() -> Any:
        nonlocal external_called
        external_called = True
        raise AssertionError("external client must not be constructed")

    with pytest.raises(DocumentNotFoundError):
        index_document(
            uuid4(),
            session_factory=session_factory,
            embedding_client_factory=fail_if_called,
            vector_store_factory=fail_if_called,
        )

    assert external_called is False


def test_index_document_without_chunks_fails_before_external_clients(
    indexed_document_database: tuple[Any, UUID, list[TrackingSession]],
) -> None:
    """A known Document without Chunks also fails before Qdrant and BGE."""
    session_factory, _, _ = indexed_document_database
    document_id = uuid4()
    with session_factory() as session:
        with session.begin():
            session.add(
                Document(
                    id=document_id,
                    filename="empty.txt",
                    size=1,
                    status="ready",
                    extracted_text="empty",
                )
            )
    external_called = False

    def fail_if_called() -> Any:
        nonlocal external_called
        external_called = True
        raise AssertionError("external client must not be constructed")

    with pytest.raises(DocumentChunksNotFoundError):
        index_document(
            document_id,
            session_factory=session_factory,
            embedding_client_factory=fail_if_called,
            vector_store_factory=fail_if_called,
        )

    assert external_called is False


def test_index_summary_excludes_content_and_vectors(
    indexed_document_database: tuple[Any, UUID, list[TrackingSession]],
) -> None:
    """Successful command output contains no source text or vector values."""
    session_factory, document_id, _ = indexed_document_database
    store = StubVectorStore()
    summary = index_document(
        document_id,
        session_factory=session_factory,
        embedding_client_factory=StubEmbeddingClient,  # type: ignore[arg-type]
        vector_store_factory=lambda: store,  # type: ignore[arg-type]
    )
    output = StringIO()

    print_summary(summary, output=output)
    rendered = output.getvalue()

    assert "collection: test-documents" in rendered
    assert "chunk_count: 2" in rendered
    assert "embedding_dimension: 512" in rendered
    assert "status: success" in rendered
    assert "zero" not in rendered
    assert "one" not in rendered
    assert "[" not in rendered


def test_init_qdrant_does_not_require_embedding_or_database() -> None:
    """The initialization command invokes only the supplied vector store."""
    store = StubVectorStore()

    summary = initialize_qdrant(
        vector_store_factory=lambda: store,  # type: ignore[arg-type]
    )

    assert store.initialized is True
    assert summary.collection == "test-documents"
    assert summary.dimension == 512
    assert summary.distance == "Cosine"
