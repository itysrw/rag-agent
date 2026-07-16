"""Create or validate the fixed Day 7 Qdrant collection."""

from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import TextIO

from loguru import logger
from pydantic import ValidationError

from backend.app.core.config import EMBEDDING_DIMENSION
from backend.app.services.qdrant_store import (
    QdrantStoreError,
    QdrantVectorStore,
    get_qdrant_vector_store,
)


@dataclass(frozen=True, slots=True)
class QdrantInitializationSummary:
    """Safe collection initialization output."""

    collection: str
    dimension: int
    distance: str


VectorStoreFactory = Callable[[], QdrantVectorStore]


def initialize_qdrant(
    *,
    vector_store_factory: VectorStoreFactory = get_qdrant_vector_store,
) -> QdrantInitializationSummary:
    """Create or validate the collection without loading BGE or PostgreSQL."""
    store = vector_store_factory()
    store.initialize_collection()
    return QdrantInitializationSummary(
        collection=store.settings.collection,
        dimension=EMBEDDING_DIMENSION,
        distance="Cosine",
    )


def print_summary(
    summary: QdrantInitializationSummary,
    *,
    output: TextIO = sys.stdout,
) -> None:
    """Print only the fixed collection schema and status."""
    print(f"collection: {summary.collection}", file=output)
    print(f"dimension: {summary.dimension}", file=output)
    print(f"distance: {summary.distance}", file=output)
    print("status: ready", file=output)


def main() -> int:
    """Run the explicit collection initialization command."""
    try:
        summary = initialize_qdrant()
    except ValidationError as exc:
        logger.error("Qdrant configuration invalid: {}", type(exc).__name__)
        print("error: the Qdrant configuration is invalid", file=sys.stderr)
        return 1
    except QdrantStoreError as exc:
        logger.error("Qdrant initialization failed: {}", type(exc).__name__)
        print("error: the Qdrant service is unavailable", file=sys.stderr)
        return 1

    print_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
