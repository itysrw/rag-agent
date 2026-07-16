"""Unit tests for the strict Day 7 Qdrant adapter."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError
from qdrant_client import QdrantClient
from qdrant_client.http import models

from backend.app.core.config import (
    EMBEDDING_MODEL_NAME,
    EMBEDDING_MODEL_REVISION,
    QdrantSettings,
)
from backend.app.services.qdrant_store import (
    QDRANT_SCHEMA_VERSION,
    QdrantCollectionMismatchError,
    QdrantResultError,
    QdrantUnavailableError,
    QdrantVectorStore,
    VectorizedChunk,
)


def build_settings(**overrides: Any) -> QdrantSettings:
    """Build settings without reading the repository environment file."""
    return QdrantSettings(_env_file=None, **overrides)


def basis_vector(position: int = 0) -> tuple[float, ...]:
    """Return one finite normalized 512-dimensional vector."""
    values = [0.0] * 512
    values[position] = 1.0
    return tuple(values)


def vectorized_chunk(index: int) -> VectorizedChunk:
    """Return one complete point input with stable UUID identities."""
    return VectorizedChunk(
        chunk_id=uuid4(),
        doc_id=uuid4(),
        chunk_index=index,
        content=f"content-{index}",
        page=index + 1,
        filename="policy.pdf",
        metadata={"token_count": index + 1},
        vector=basis_vector(index % 512),
    )


class FakeQdrantClient:
    """Record Qdrant calls while exposing controlled collection state."""

    def __init__(
        self,
        *,
        exists: bool = True,
        vectors: Any | None = None,
        metadata: dict[str, Any] | None = None,
        query_points: list[Any] | None = None,
    ) -> None:
        self.exists = exists
        self.vectors = vectors or models.VectorParams(
            size=512,
            distance=models.Distance.COSINE,
        )
        self.metadata = (
            metadata
            if metadata is not None
            else {
                "schema_version": QDRANT_SCHEMA_VERSION,
                "embedding_model": EMBEDDING_MODEL_NAME,
                "embedding_revision": EMBEDDING_MODEL_REVISION,
            }
        )
        self.returned_points = query_points or []
        self.exists_calls = 0
        self.create_calls: list[dict[str, Any]] = []
        self.upsert_calls: list[dict[str, Any]] = []
        self.query_calls: list[dict[str, Any]] = []
        self.raise_exists: BaseException | None = None
        self.fail_upsert_call: int | None = None

    def collection_exists(self, collection_name: str, **kwargs: Any) -> bool:
        del collection_name, kwargs
        self.exists_calls += 1
        if self.raise_exists is not None:
            raise self.raise_exists
        return self.exists

    def create_collection(
        self,
        collection_name: str,
        vectors_config: models.VectorParams,
        **kwargs: Any,
    ) -> bool:
        self.create_calls.append(
            {
                "collection_name": collection_name,
                "vectors_config": vectors_config,
                **kwargs,
            }
        )
        self.exists = True
        self.vectors = vectors_config
        return True

    def get_collection(self, collection_name: str, **kwargs: Any) -> Any:
        del collection_name, kwargs
        return SimpleNamespace(
            config=SimpleNamespace(
                params=SimpleNamespace(vectors=self.vectors),
                metadata=self.metadata,
            )
        )

    def upsert(
        self,
        collection_name: str,
        points: list[models.PointStruct],
        **kwargs: Any,
    ) -> None:
        self.upsert_calls.append(
            {
                "collection_name": collection_name,
                "points": points,
                **kwargs,
            }
        )
        if self.fail_upsert_call == len(self.upsert_calls):
            raise ConnectionError("offline")

    def query_points(self, collection_name: str, **kwargs: Any) -> Any:
        self.query_calls.append({"collection_name": collection_name, **kwargs})
        return SimpleNamespace(points=self.returned_points)


@pytest.mark.parametrize(
    "overrides",
    [
        {"host": " "},
        {"port": 0},
        {"port": 65536},
        {"collection": "\n"},
        {"timeout_seconds": 0},
        {"upsert_batch_size": 0},
        {"upsert_batch_size": 33},
    ],
)
def test_qdrant_settings_reject_invalid_values(overrides: dict[str, Any]) -> None:
    """Day 7 configuration cannot expand beyond the local fixed contract."""
    with pytest.raises(ValidationError):
        build_settings(**overrides)


def test_qdrant_settings_build_trimmed_local_url() -> None:
    """The REST URL contains no credentials and normalizes the host."""
    settings = build_settings(host=" 127.0.0.1 ", port=6333, collection=" docs ")

    assert settings.build_url() == "http://127.0.0.1:6333"
    assert settings.collection == "docs"
    assert settings.upsert_batch_size == 32


def test_initialize_creates_fixed_unnamed_cosine_collection() -> None:
    """A missing collection is created once without destructive recreation."""
    client = FakeQdrantClient(exists=False)
    store = QdrantVectorStore(build_settings(), client=client)

    store.initialize_collection()

    assert len(client.create_calls) == 1
    call = client.create_calls[0]
    assert call["collection_name"] == "documents"
    assert call["vectors_config"].size == 512
    assert call["vectors_config"].distance == models.Distance.COSINE
    assert call["metadata"]["schema_version"] == 1
    assert "embedding_revision" in call["metadata"]
    assert not hasattr(client, "recreate_collection")


def test_initialize_validates_existing_collection_without_creating() -> None:
    """An existing correct collection is preserved."""
    client = FakeQdrantClient()
    store = QdrantVectorStore(build_settings(), client=client)

    store.initialize_collection()

    assert client.create_calls == []


def test_collection_metadata_mismatch_fails_without_recreation() -> None:
    """Each incompatible model or payload schema marker fails closed."""
    expected_metadata: dict[str, Any] = {
        "schema_version": QDRANT_SCHEMA_VERSION,
        "embedding_model": EMBEDDING_MODEL_NAME,
        "embedding_revision": EMBEDDING_MODEL_REVISION,
    }
    incompatible_values: dict[str, Any] = {
        "schema_version": QDRANT_SCHEMA_VERSION + 1,
        "embedding_model": "other-embedding-model",
        "embedding_revision": "other-revision",
    }

    for field, incompatible_value in incompatible_values.items():
        metadata = {**expected_metadata, field: incompatible_value}
        client = FakeQdrantClient(metadata=metadata)
        store = QdrantVectorStore(build_settings(), client=client)

        with pytest.raises(QdrantCollectionMismatchError):
            store.validate_collection()

        assert client.create_calls == []


@pytest.mark.parametrize(
    "vectors",
    [
        models.VectorParams(size=384, distance=models.Distance.COSINE),
        models.VectorParams(size=512, distance=models.Distance.DOT),
        {"named": models.VectorParams(size=512, distance=models.Distance.COSINE)},
    ],
)
def test_collection_mismatch_fails_without_recreation(vectors: Any) -> None:
    """Wrong dimensions, distance, or named vectors fail closed."""
    client = FakeQdrantClient(vectors=vectors)
    store = QdrantVectorStore(build_settings(), client=client)

    with pytest.raises(QdrantCollectionMismatchError):
        store.validate_collection()

    assert client.create_calls == []


def test_upsert_uses_stable_ids_payload_wait_and_bounded_batches() -> None:
    """Sixty-five points are written as 32/32/1 completed operations."""
    client = FakeQdrantClient()
    store = QdrantVectorStore(build_settings(), client=client)
    chunks = [vectorized_chunk(index) for index in range(65)]

    written = store.upsert_chunks(chunks)

    assert written == 65
    assert [len(call["points"]) for call in client.upsert_calls] == [32, 32, 1]
    assert all(call["wait"] is True for call in client.upsert_calls)
    first_point = client.upsert_calls[0]["points"][0]
    assert first_point.id == str(chunks[0].chunk_id)
    assert first_point.payload == {
        "chunk_id": str(chunks[0].chunk_id),
        "doc_id": str(chunks[0].doc_id),
        "chunk_index": 0,
        "content": "content-0",
        "page": 1,
        "filename": "policy.pdf",
        "metadata": {"token_count": 1},
    }


def test_empty_upsert_does_not_contact_qdrant() -> None:
    """No collection check or write is needed for an empty input."""
    client = FakeQdrantClient()
    store = QdrantVectorStore(build_settings(), client=client)

    assert store.upsert_chunks([]) == 0
    assert client.exists_calls == 0
    assert client.upsert_calls == []


def test_partial_upsert_failure_is_explicit_and_safe_to_retry() -> None:
    """A later failed batch is reported without pretending earlier writes rolled back."""
    client = FakeQdrantClient()
    client.fail_upsert_call = 2
    store = QdrantVectorStore(build_settings(), client=client)

    with pytest.raises(QdrantUnavailableError):
        store.upsert_chunks([vectorized_chunk(index) for index in range(33)])

    assert [len(call["points"]) for call in client.upsert_calls] == [32, 1]


def scored_point(chunk: VectorizedChunk, score: float) -> Any:
    """Build one Qdrant-like scored point from a complete payload."""
    return SimpleNamespace(
        id=str(chunk.chunk_id),
        score=score,
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


def test_search_uses_query_points_and_excludes_vectors() -> None:
    """The current query API returns score-sorted validated payloads only."""
    low = vectorized_chunk(0)
    high = vectorized_chunk(1)
    client = FakeQdrantClient(
        query_points=[scored_point(low, 0.5), scored_point(high, 0.9)]
    )
    store = QdrantVectorStore(build_settings(), client=client)

    results = store.search(basis_vector(), limit=5)

    assert [result.chunk_id for result in results] == [high.chunk_id, low.chunk_id]
    assert len(client.query_calls) == 1
    call = client.query_calls[0]
    assert call["limit"] == 5
    assert call["with_payload"] is True
    assert call["with_vectors"] is False
    assert "search" not in client.__class__.__dict__


def test_search_does_not_create_a_missing_collection() -> None:
    """Online search fails safely instead of changing collection state."""
    client = FakeQdrantClient(exists=False)
    store = QdrantVectorStore(build_settings(), client=client)

    with pytest.raises(QdrantCollectionMismatchError):
        store.search(basis_vector(), limit=5)

    assert client.create_calls == []
    assert client.query_calls == []


def test_invalid_qdrant_payload_fails_without_partial_results() -> None:
    """A missing required payload field invalidates the whole response."""
    chunk = vectorized_chunk(0)
    point = scored_point(chunk, 0.9)
    del point.payload["content"]
    client = FakeQdrantClient(query_points=[point])
    store = QdrantVectorStore(build_settings(), client=client)

    with pytest.raises(QdrantResultError):
        store.search(basis_vector(), limit=5)


def test_search_rejects_non_scalar_metadata_values() -> None:
    """Nested or non-finite metadata fails safely inside the adapter."""
    invalid_metadata_values: list[dict[str, Any]] = [
        {"nested": {"secret": "private-value"}},
        {"nested": ["private-value"]},
        {"confidence": float("nan"), "label": "private-value"},
    ]

    for metadata in invalid_metadata_values:
        point = scored_point(vectorized_chunk(0), 0.9)
        point.payload["metadata"] = metadata
        client = FakeQdrantClient(query_points=[point])
        store = QdrantVectorStore(build_settings(), client=client)

        with pytest.raises(QdrantResultError) as error:
            store.search(basis_vector(), limit=5)

        assert "private-value" not in str(error.value)


def test_connection_failure_is_wrapped_without_endpoint_details() -> None:
    """Transport failures become one safe adapter exception."""
    client = FakeQdrantClient()
    client.raise_exists = ConnectionError("http://secret-host:6333")
    store = QdrantVectorStore(build_settings(), client=client)

    with pytest.raises(QdrantUnavailableError) as error:
        store.validate_collection()

    assert "secret-host" not in str(error.value)


def test_actual_qdrant_client_local_mode_supports_idempotent_round_trip() -> None:
    """Exercise the pinned client's real collection, upsert, and query models."""
    client = QdrantClient(":memory:")
    store = QdrantVectorStore(
        build_settings(collection="local-round-trip"),
        client=client,
    )
    chunks = [vectorized_chunk(0), vectorized_chunk(1)]
    try:
        store.initialize_collection()
        assert store.upsert_chunks(chunks) == 2
        assert store.upsert_chunks(chunks) == 2

        results = store.search(chunks[0].vector, limit=5)

        assert len(results) == 2
        assert results[0].chunk_id == chunks[0].chunk_id
        assert results[0].metadata == chunks[0].metadata
    finally:
        client.close()
