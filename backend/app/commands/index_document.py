"""Explicitly embed PostgreSQL Chunks and upsert them into Qdrant."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import TextIO
from uuid import UUID

from loguru import logger
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.commands.embed_document import EmbeddingConfigurationError
from backend.app.core.database import (
    DatabaseConfigurationError,
    get_session_factory,
)
from backend.app.models.chunk import Chunk
from backend.app.models.document import Document
from backend.app.services.embedding import (
    ChunkEmbeddingInput,
    EmbeddingClient,
    EmbeddingError,
    embed_chunks,
    get_embedding_client,
)
from backend.app.services.qdrant_store import (
    QdrantResultError,
    QdrantStoreError,
    QdrantVectorStore,
    VectorizedChunk,
    get_qdrant_vector_store,
)


class DocumentIndexingError(RuntimeError):
    """Base class for safe document indexing command failures."""


class DocumentNotFoundError(DocumentIndexingError):
    """Raised when the requested Document does not exist."""


class DocumentChunksNotFoundError(DocumentIndexingError):
    """Raised before external work when a Document has no Chunks."""


class QdrantConfigurationError(DocumentIndexingError):
    """Raised when local Qdrant settings are invalid."""


@dataclass(frozen=True, slots=True)
class IndexSummary:
    """Safe indexing output without document text or vectors."""

    document_id: UUID
    collection: str
    chunk_count: int
    embedding_dimension: int


SessionFactory = Callable[[], Session]
EmbeddingClientFactory = Callable[[], EmbeddingClient]
VectorStoreFactory = Callable[[], QdrantVectorStore]


def index_document(
    document_id: UUID,
    *,
    session_factory: SessionFactory | None = None,
    embedding_client_factory: EmbeddingClientFactory = get_embedding_client,
    vector_store_factory: VectorStoreFactory = get_qdrant_vector_store,
) -> IndexSummary:
    """Read ordered Chunks, close PostgreSQL, then embed and upsert them."""
    resolved_session_factory = session_factory or get_session_factory()
    with resolved_session_factory() as session:
        document = session.get(Document, document_id)
        if document is None:
            raise DocumentNotFoundError(
                f"document_id={document_id} does not exist"
            )
        chunks = session.scalars(
            select(Chunk)
            .where(Chunk.doc_id == document_id)
            .order_by(Chunk.chunk_index)
        ).all()
        filename = document.filename

    if not chunks:
        raise DocumentChunksNotFoundError(
            f"document_id={document_id} has no persisted chunks"
        )

    try:
        vector_store = vector_store_factory()
    except ValidationError as exc:
        raise QdrantConfigurationError(
            "The Qdrant configuration is invalid."
        ) from exc
    vector_store.initialize_collection()

    try:
        embedding_client = embedding_client_factory()
    except ValidationError as exc:
        raise EmbeddingConfigurationError(
            "The embedding configuration is invalid."
        ) from exc

    embedded = embed_chunks(
        [
            ChunkEmbeddingInput(chunk_id=chunk.chunk_id, content=chunk.content)
            for chunk in chunks
        ],
        embedding_client,
    )
    vectorized = [
        VectorizedChunk(
            chunk_id=chunk.chunk_id,
            doc_id=chunk.doc_id,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            page=chunk.page,
            filename=filename,
            metadata=dict(chunk.chunk_metadata),
            vector=embedded_chunk.vector,
        )
        for chunk, embedded_chunk in zip(chunks, embedded, strict=True)
    ]
    written = vector_store.upsert_chunks(vectorized)
    if written != len(vectorized):
        raise QdrantResultError(
            "The Qdrant upsert count does not match the Chunk count."
        )

    return IndexSummary(
        document_id=document_id,
        collection=vector_store.settings.collection,
        chunk_count=written,
        embedding_dimension=embedding_client.dimension,
    )


def print_summary(summary: IndexSummary, *, output: TextIO = sys.stdout) -> None:
    """Print only safe indexing identifiers, counts, and status."""
    print(f"document_id: {summary.document_id}", file=output)
    print(f"collection: {summary.collection}", file=output)
    print(f"chunk_count: {summary.chunk_count}", file=output)
    print(f"embedding_dimension: {summary.embedding_dimension}", file=output)
    print("status: success", file=output)


def build_parser() -> argparse.ArgumentParser:
    """Build the explicit document indexing command parser."""
    parser = argparse.ArgumentParser(
        description="Embed one document's Chunks and upsert them into Qdrant.",
    )
    parser.add_argument(
        "--document-id",
        required=True,
        type=UUID,
        help="UUID of the persisted document to index.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the explicit, idempotent document indexing command."""
    arguments = build_parser().parse_args(argv)
    try:
        summary = index_document(arguments.document_id)
    except (DatabaseConfigurationError, ValidationError, SQLAlchemyError) as exc:
        logger.error("Document indexing database failure: {}", type(exc).__name__)
        print("error: the document database is unavailable", file=sys.stderr)
        return 1
    except DocumentIndexingError as exc:
        logger.error("Document indexing failed: {}", type(exc).__name__)
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except EmbeddingError as exc:
        logger.error("Document embedding failed: {}", type(exc).__name__)
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except QdrantStoreError as exc:
        logger.error("Document Qdrant indexing failed: {}", type(exc).__name__)
        print("error: the Qdrant indexing operation failed", file=sys.stderr)
        return 1

    print_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
