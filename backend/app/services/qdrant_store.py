"""Qdrant collection, indexing, and retrieval boundaries for Day 7."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from numbers import Real
from typing import Any, Protocol
from uuid import UUID

from qdrant_client import QdrantClient
from qdrant_client.http import models

from backend.app.core.config import (
    EMBEDDING_DIMENSION,
    EMBEDDING_MODEL_NAME,
    EMBEDDING_MODEL_REVISION,
    QdrantSettings,
    get_qdrant_settings,
)
from backend.app.models.chunk import JSONScalar

QDRANT_SCHEMA_VERSION = 1


class QdrantStoreError(RuntimeError):
    """Base class for safe Qdrant adapter failures."""


class QdrantUnavailableError(QdrantStoreError):
    """Raised when the configured Qdrant service cannot complete an operation."""


class QdrantCollectionMismatchError(QdrantStoreError):
    """Raised when the collection is missing or has an unsafe vector schema."""


class QdrantResultError(QdrantStoreError):
    """Raised when Qdrant returns an invalid point or payload."""


@dataclass(frozen=True, slots=True)
class VectorizedChunk:
    """One PostgreSQL Chunk and its validated document vector."""

    chunk_id: UUID
    doc_id: UUID
    chunk_index: int
    content: str
    page: int
    filename: str
    metadata: dict[str, JSONScalar]
    vector: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """One safe payload returned by a Qdrant similarity query."""

    chunk_id: UUID
    doc_id: UUID
    chunk_index: int
    content: str
    page: int
    filename: str
    metadata: dict[str, JSONScalar]
    score: float


class QdrantClientProtocol(Protocol):
    """Qdrant client surface used by the adapter and its unit tests."""

    def collection_exists(self, collection_name: str, **kwargs: Any) -> bool: ...

    def create_collection(
        self,
        collection_name: str,
        vectors_config: models.VectorParams,
        **kwargs: Any,
    ) -> bool: ...

    def get_collection(self, collection_name: str, **kwargs: Any) -> Any: ...

    def upsert(
        self,
        collection_name: str,
        points: Sequence[models.PointStruct],
        **kwargs: Any,
    ) -> Any: ...

    def query_points(self, collection_name: str, **kwargs: Any) -> Any: ...


class QdrantVectorStore:
    """Strict unnamed-vector Qdrant adapter with no implicit collection creation."""

    def __init__(
        self,
        settings: QdrantSettings,
        *,
        client: QdrantClientProtocol | None = None,
    ) -> None:
        self.settings = settings
        self._client = client or QdrantClient(
            url=settings.build_url(),
            timeout=settings.timeout_seconds,
            prefer_grpc=False,
        )

    def initialize_collection(self) -> None:
        """Create the fixed collection when absent, otherwise validate it."""
        if not self._collection_exists():
            try:
                created = self._client.create_collection(
                    collection_name=self.settings.collection,
                    vectors_config=models.VectorParams(
                        size=EMBEDDING_DIMENSION,
                        distance=models.Distance.COSINE,
                    ),
                    metadata={
                        "schema_version": QDRANT_SCHEMA_VERSION,
                        "embedding_model": EMBEDDING_MODEL_NAME,
                        "embedding_revision": EMBEDDING_MODEL_REVISION,
                    },
                )
            except MemoryError:
                raise
            except Exception as exc:
                raise QdrantUnavailableError(
                    "The Qdrant collection could not be initialized."
                ) from exc
            if created is False:
                raise QdrantUnavailableError(
                    "The Qdrant collection could not be initialized."
                )

        self.validate_collection()

    def validate_collection(self) -> None:
        """Require one unnamed 512-dimensional Cosine vector configuration."""
        if not self._collection_exists():
            raise QdrantCollectionMismatchError(
                "The Qdrant collection is not initialized."
            )

        try:
            collection = self._client.get_collection(self.settings.collection)
        except MemoryError:
            raise
        except Exception as exc:
            raise QdrantUnavailableError(
                "The Qdrant collection could not be inspected."
            ) from exc

        try:
            vectors = collection.config.params.vectors
            metadata = collection.config.metadata
            is_named_vectors = isinstance(vectors, Mapping)
            size = None if is_named_vectors else vectors.size
            distance = None if is_named_vectors else vectors.distance
        except (AttributeError, TypeError) as exc:
            raise QdrantCollectionMismatchError(
                "The Qdrant collection vector configuration is invalid."
            ) from exc

        if (
            is_named_vectors
            or isinstance(size, bool)
            or size != EMBEDDING_DIMENSION
            or distance != models.Distance.COSINE
        ):
            raise QdrantCollectionMismatchError(
                "The Qdrant collection must use one unnamed 512-dimensional "
                "Cosine vector."
            )

        expected_metadata = {
            "schema_version": QDRANT_SCHEMA_VERSION,
            "embedding_model": EMBEDDING_MODEL_NAME,
            "embedding_revision": EMBEDDING_MODEL_REVISION,
        }
        if not isinstance(metadata, Mapping) or any(
            type(metadata.get(field)) is not type(expected_value)
            or metadata.get(field) != expected_value
            for field, expected_value in expected_metadata.items()
        ):
            raise QdrantCollectionMismatchError(
                "The Qdrant collection metadata is incompatible."
            )

    def upsert_chunks(self, chunks: Sequence[VectorizedChunk]) -> int:
        """Upsert stable Chunk UUID points in bounded, completed batches."""
        if not chunks:
            return 0

        points = [_build_point(chunk) for chunk in chunks]
        self.validate_collection()
        for start in range(0, len(points), self.settings.upsert_batch_size):
            batch = points[start : start + self.settings.upsert_batch_size]
            try:
                self._client.upsert(
                    collection_name=self.settings.collection,
                    points=batch,
                    wait=True,
                )
            except MemoryError:
                raise
            except Exception as exc:
                raise QdrantUnavailableError(
                    "The Qdrant point upsert did not complete."
                ) from exc
        return len(points)

    def search(
        self,
        query_vector: Sequence[float],
        *,
        limit: int,
        doc_id: UUID | None = None,
    ) -> list[RetrievedChunk]:
        """Query validated payloads without returning stored vectors."""
        if isinstance(limit, bool) or limit <= 0:
            raise ValueError("limit must be positive")
        if doc_id is not None and not isinstance(doc_id, UUID):
            raise ValueError("doc_id must be a UUID or None")
        vector = _validated_vector(query_vector)
        self.validate_collection()

        query_kwargs: dict[str, Any] = {}
        if doc_id is not None:
            query_kwargs["query_filter"] = models.Filter(
                must=[
                    models.FieldCondition(
                        key="doc_id",
                        match=models.MatchValue(value=str(doc_id)),
                    )
                ]
            )

        try:
            response = self._client.query_points(
                collection_name=self.settings.collection,
                query=vector,
                limit=limit,
                with_payload=True,
                with_vectors=False,
                **query_kwargs,
            )
        except MemoryError:
            raise
        except Exception as exc:
            raise QdrantUnavailableError(
                "The Qdrant similarity query failed."
            ) from exc

        points = getattr(response, "points", None)
        if not isinstance(points, list) or len(points) > limit:
            raise QdrantResultError("Qdrant returned an invalid result set.")

        results = [_parse_scored_point(point) for point in points]
        if doc_id is not None and any(
            result.doc_id != doc_id for result in results
        ):
            raise QdrantResultError(
                "Qdrant returned a result outside the requested document."
            )
        results.sort(key=lambda item: item.score, reverse=True)
        return results

    def _collection_exists(self) -> bool:
        try:
            return self._client.collection_exists(self.settings.collection)
        except MemoryError:
            raise
        except Exception as exc:
            raise QdrantUnavailableError(
                "The Qdrant collection state is unavailable."
            ) from exc


def _build_point(chunk: VectorizedChunk) -> models.PointStruct:
    if not isinstance(chunk.chunk_id, UUID) or not isinstance(chunk.doc_id, UUID):
        raise QdrantResultError("Chunk identities must be UUID values.")
    if isinstance(chunk.chunk_index, bool) or chunk.chunk_index < 0:
        raise QdrantResultError("Chunk index must be nonnegative.")
    if not isinstance(chunk.content, str) or not chunk.content.strip():
        raise QdrantResultError("Chunk content must not be blank.")
    if isinstance(chunk.page, bool) or chunk.page < 1:
        raise QdrantResultError("Chunk page must be positive.")
    if not isinstance(chunk.filename, str) or not chunk.filename.strip():
        raise QdrantResultError("Chunk filename must not be blank.")
    if not isinstance(chunk.metadata, dict):
        raise QdrantResultError("Chunk metadata must be an object.")

    return models.PointStruct(
        id=str(chunk.chunk_id),
        vector=_validated_vector(chunk.vector),
        payload={
            "chunk_id": str(chunk.chunk_id),
            "doc_id": str(chunk.doc_id),
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
            "page": chunk.page,
            "filename": chunk.filename,
            "metadata": dict(chunk.metadata),
        },
    )


def _validated_vector(vector: Sequence[float]) -> list[float]:
    if isinstance(vector, (str, bytes)):
        raise QdrantResultError("The vector is invalid.")
    try:
        values = list(vector)
    except TypeError as exc:
        raise QdrantResultError("The vector is invalid.") from exc
    if len(values) != EMBEDDING_DIMENSION:
        raise QdrantResultError("The vector dimension must be 512.")

    converted: list[float] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, Real):
            raise QdrantResultError("The vector must contain numeric values.")
        converted_value = float(value)
        if not math.isfinite(converted_value):
            raise QdrantResultError("The vector must contain finite values.")
        converted.append(converted_value)

    norm = math.sqrt(sum(value * value for value in converted))
    if not math.isclose(norm, 1.0, rel_tol=1e-4, abs_tol=1e-4):
        raise QdrantResultError("The vector must be normalized.")
    return converted


def _parse_scored_point(point: Any) -> RetrievedChunk:
    point_id = getattr(point, "id", None)
    if isinstance(point_id, (int, bool)):
        raise QdrantResultError("Qdrant returned a non-UUID point ID.")
    try:
        chunk_id = UUID(str(point_id))
    except (TypeError, ValueError) as exc:
        raise QdrantResultError("Qdrant returned a non-UUID point ID.") from exc

    payload = getattr(point, "payload", None)
    if not isinstance(payload, dict):
        raise QdrantResultError("Qdrant returned an invalid payload.")

    try:
        payload_chunk_id = UUID(str(payload["chunk_id"]))
        doc_id = UUID(str(payload["doc_id"]))
        chunk_index = payload["chunk_index"]
        content = payload["content"]
        page = payload["page"]
        filename = payload["filename"]
        metadata = payload["metadata"]
    except (KeyError, TypeError, ValueError) as exc:
        raise QdrantResultError("Qdrant returned an invalid payload.") from exc

    if payload_chunk_id != chunk_id:
        raise QdrantResultError("Qdrant point and payload identities do not match.")
    if isinstance(chunk_index, bool) or not isinstance(chunk_index, int) or chunk_index < 0:
        raise QdrantResultError("Qdrant returned an invalid chunk index.")
    if not isinstance(content, str) or not content.strip():
        raise QdrantResultError("Qdrant returned invalid chunk content.")
    if isinstance(page, bool) or not isinstance(page, int) or page < 1:
        raise QdrantResultError("Qdrant returned an invalid page.")
    if not isinstance(filename, str) or not filename.strip():
        raise QdrantResultError("Qdrant returned an invalid filename.")
    validated_metadata = _validated_metadata(metadata)

    score = getattr(point, "score", None)
    if isinstance(score, bool) or not isinstance(score, Real):
        raise QdrantResultError("Qdrant returned an invalid score.")
    converted_score = float(score)
    if not math.isfinite(converted_score):
        raise QdrantResultError("Qdrant returned an invalid score.")

    return RetrievedChunk(
        chunk_id=chunk_id,
        doc_id=doc_id,
        chunk_index=chunk_index,
        content=content,
        page=page,
        filename=filename,
        metadata=validated_metadata,
        score=converted_score,
    )


def _validated_metadata(value: Any) -> dict[str, JSONScalar]:
    if not isinstance(value, dict):
        raise QdrantResultError("Qdrant returned invalid metadata.")

    validated: dict[str, JSONScalar] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise QdrantResultError("Qdrant returned invalid metadata.")
        if item is None or isinstance(item, (str, bool, int)):
            validated[key] = item
            continue
        if isinstance(item, float) and math.isfinite(item):
            validated[key] = item
            continue
        raise QdrantResultError("Qdrant returned invalid metadata.")
    return validated


@lru_cache
def get_qdrant_vector_store() -> QdrantVectorStore:
    """Return one lazy process-wide adapter for the configured collection."""
    return QdrantVectorStore(get_qdrant_settings())
