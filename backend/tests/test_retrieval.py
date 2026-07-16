"""Tests for fixed Top-5 retrieval orchestration and HTTP mapping."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.app.api.retrieval import require_retrieval_service
from backend.app.main import app
from backend.app.services.embedding import (
    EmbeddingError,
    EmbeddingInputTooLongError,
)
from backend.app.services.qdrant_store import (
    QdrantCollectionMismatchError,
    QdrantResultError,
    QdrantUnavailableError,
    RetrievedChunk,
)
from backend.app.services.retrieval import RETRIEVAL_TOP_K, RetrievalService


def basis_vector() -> tuple[float, ...]:
    """Return one normalized vector for service orchestration tests."""
    return (1.0,) + (0.0,) * 511


class StubEmbeddingClient:
    """Record the query presented to the embedding boundary."""

    def __init__(self) -> None:
        self.queries: list[str] = []

    def embed_query(self, query: str) -> tuple[float, ...]:
        self.queries.append(query)
        return basis_vector()


class StubVectorStore:
    """Record the fixed search limit and return controlled results."""

    def __init__(self, results: list[RetrievedChunk] | None = None) -> None:
        self.results = results or []
        self.calls: list[dict[str, Any]] = []

    def search(
        self,
        query_vector: tuple[float, ...],
        *,
        limit: int,
    ) -> list[RetrievedChunk]:
        self.calls.append({"query_vector": query_vector, "limit": limit})
        return self.results


def retrieved_chunk() -> RetrievedChunk:
    """Return one complete API-safe retrieval result."""
    return RetrievedChunk(
        chunk_id=uuid4(),
        doc_id=uuid4(),
        chunk_index=0,
        content="报销票据每月二十五日前提交。",
        page=1,
        filename="policy.pdf",
        metadata={"token_count": 12},
        score=0.91,
    )


def test_retrieval_service_uses_query_embedding_and_fixed_top_five() -> None:
    """Day 7 callers cannot select a different result limit."""
    embedding = StubEmbeddingClient()
    vector_store = StubVectorStore([retrieved_chunk()])
    service = RetrievalService(embedding, vector_store)  # type: ignore[arg-type]

    results = service.search("报销时间")

    assert len(results) == 1
    assert embedding.queries == ["报销时间"]
    assert vector_store.calls == [
        {"query_vector": basis_vector(), "limit": RETRIEVAL_TOP_K}
    ]
    assert RETRIEVAL_TOP_K == 5


class StubRetrievalService:
    """API dependency replacement with controlled success or failure."""

    def __init__(
        self,
        *,
        results: list[RetrievedChunk] | None = None,
        failure: BaseException | None = None,
    ) -> None:
        self.results = results or []
        self.failure = failure
        self.queries: list[str] = []

    def search(self, query: str) -> list[RetrievedChunk]:
        self.queries.append(query)
        if self.failure is not None:
            raise self.failure
        return self.results


@pytest.fixture
def api_client() -> Iterator[tuple[TestClient, StubRetrievalService]]:
    """Provide a successful retrieval endpoint without model or Qdrant calls."""
    service = StubRetrievalService(results=[retrieved_chunk()])
    app.dependency_overrides[require_retrieval_service] = lambda: service
    try:
        with TestClient(app) as client:
            yield client, service
    finally:
        app.dependency_overrides.clear()


def test_search_api_returns_safe_payload_without_vector(
    api_client: tuple[TestClient, StubRetrievalService],
) -> None:
    """The endpoint trims the query and never serializes stored vectors."""
    client, service = api_client

    response = client.post("/retrieval/search", json={"query": "  报销时间  "})

    assert response.status_code == 200
    assert service.queries == ["报销时间"]
    body = response.json()
    assert body["results"][0]["content"] == "报销票据每月二十五日前提交。"
    assert body["results"][0]["page"] == 1
    assert body["results"][0]["score"] == 0.91
    assert "vector" not in body["results"][0]


def test_search_api_rejects_query_over_character_limit_before_service(
    api_client: tuple[TestClient, StubRetrievalService],
) -> None:
    """An extremely large query is rejected before model or Qdrant work."""
    client, service = api_client

    response = client.post("/retrieval/search", json={"query": "x" * 100_000})

    assert response.status_code == 422
    assert service.queries == []


@pytest.mark.parametrize(
    "payload",
    [
        {"query": "   "},
        {"query": "valid", "top_k": 10},
        {"query": "valid", "doc_id": str(uuid4())},
    ],
)
def test_search_api_rejects_blank_or_day9_parameters(
    api_client: tuple[TestClient, StubRetrievalService],
    payload: dict[str, Any],
) -> None:
    """The Day 7 request schema contains only one nonblank query."""
    client, service = api_client

    response = client.post("/retrieval/search", json=payload)

    assert response.status_code == 422
    assert service.queries == []


@pytest.mark.parametrize(
    ("failure", "expected_status", "expected_detail"),
    [
        (
            EmbeddingInputTooLongError(
                input_index=0,
                token_count=600,
                max_tokens=512,
            ),
            422,
            "The retrieval query exceeds the embedding model limit.",
        ),
        (
            EmbeddingError("private model path"),
            503,
            "The retrieval service is unavailable.",
        ),
        (
            QdrantUnavailableError("http://private-host:6333"),
            503,
            "The retrieval service is unavailable.",
        ),
        (
            QdrantCollectionMismatchError("wrong collection details"),
            503,
            "The retrieval service is unavailable.",
        ),
        (
            QdrantResultError("private payload content"),
            502,
            "The retrieval service returned an invalid result.",
        ),
    ],
)
def test_search_api_maps_failures_without_internal_details(
    failure: BaseException,
    expected_status: int,
    expected_detail: str,
) -> None:
    """Embedding and Qdrant failures expose only the approved HTTP contract."""
    service = StubRetrievalService(failure=failure)
    app.dependency_overrides[require_retrieval_service] = lambda: service
    try:
        with TestClient(app) as client:
            response = client.post("/retrieval/search", json={"query": "问题"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}
    assert str(failure) not in response.text


def test_health_does_not_resolve_retrieval_dependency() -> None:
    """Application startup and liveness remain independent of Qdrant."""
    resolved = False

    def fail_if_resolved() -> StubRetrievalService:
        nonlocal resolved
        resolved = True
        raise AssertionError("retrieval dependency must remain lazy")

    app.dependency_overrides[require_retrieval_service] = fail_if_resolved
    try:
        with TestClient(app) as client:
            response = client.get("/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert resolved is False
