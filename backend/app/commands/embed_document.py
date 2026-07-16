"""Read Chunk rows and validate local BGE embeddings without persistence."""

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

from backend.app.core.database import (
    DatabaseConfigurationError,
    get_session_factory,
)
from backend.app.models.chunk import Chunk
from backend.app.services.embedding import (
    ChunkEmbeddingInput,
    EmbeddingClient,
    EmbeddingError,
    embed_chunks,
    get_embedding_client,
)


class DocumentChunksNotFoundError(EmbeddingError):
    """Raised before model loading when a document has no persisted Chunks."""


class EmbeddingConfigurationError(EmbeddingError):
    """Raised when the local embedding configuration is invalid."""


@dataclass(frozen=True, slots=True)
class EmbeddingSummary:
    """Safe command output that excludes content and vector values."""

    document_id: UUID
    model: str
    revision: str
    device: str
    chunk_count: int
    embedding_dimension: int
    normalized: bool


SessionFactory = Callable[[], Session]
ClientFactory = Callable[[], EmbeddingClient]


def embed_document(
    document_id: UUID,
    *,
    session_factory: SessionFactory | None = None,
    client_factory: ClientFactory = get_embedding_client,
) -> EmbeddingSummary:
    """Read ordered Chunks, embed them in memory, and return a safe summary."""
    resolved_session_factory = session_factory or get_session_factory()
    with resolved_session_factory() as session:
        chunks = session.scalars(
            select(Chunk)
            .where(Chunk.doc_id == document_id)
            .order_by(Chunk.chunk_index)
        ).all()
        inputs = [
            ChunkEmbeddingInput(chunk_id=chunk.chunk_id, content=chunk.content)
            for chunk in chunks
        ]

    if not inputs:
        raise DocumentChunksNotFoundError(
            f"document_id={document_id} has no persisted chunks"
        )

    try:
        client = client_factory()
    except ValidationError as exc:
        raise EmbeddingConfigurationError(
            "The embedding configuration is invalid."
        ) from exc
    embedded = embed_chunks(inputs, client)
    return EmbeddingSummary(
        document_id=document_id,
        model=client.settings.model_name,
        revision=client.settings.model_revision,
        device=client.settings.device,
        chunk_count=len(embedded),
        embedding_dimension=client.dimension,
        normalized=client.settings.normalize_embeddings,
    )


def print_summary(summary: EmbeddingSummary, *, output: TextIO = sys.stdout) -> None:
    """Print only non-sensitive embedding validation metadata."""
    print(f"document_id: {summary.document_id}", file=output)
    print(f"model: {summary.model}", file=output)
    print(f"revision: {summary.revision}", file=output)
    print(f"device: {summary.device}", file=output)
    print(f"chunk_count: {summary.chunk_count}", file=output)
    print(f"embedding_dimension: {summary.embedding_dimension}", file=output)
    print(f"normalized: {str(summary.normalized).lower()}", file=output)
    print("status: success", file=output)


def build_parser() -> argparse.ArgumentParser:
    """Build the command parser without opening a database connection."""
    parser = argparse.ArgumentParser(
        description="Generate in-memory local BGE embeddings for one document.",
    )
    parser.add_argument(
        "--document-id",
        required=True,
        type=UUID,
        help="UUID of a document whose persisted Chunks should be embedded.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the read-only embedding validation command."""
    arguments = build_parser().parse_args(argv)
    try:
        summary = embed_document(arguments.document_id)
    except (DatabaseConfigurationError, ValidationError, SQLAlchemyError) as exc:
        logger.error("Embedding command database failure: {}", type(exc).__name__)
        print("error: the document database is unavailable", file=sys.stderr)
        return 1
    except EmbeddingError as exc:
        logger.error("Embedding command failed: {}", type(exc).__name__)
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
