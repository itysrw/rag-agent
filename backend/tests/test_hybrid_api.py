"""HTTP contract tests for the independent Day 11 Hybrid endpoint."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from backend.app.api.hybrid import require_hybrid_retrieval_service
from backend.app.main import app
from backend.app.services.bm25 import BM25IndexError, BM25UnavailableError
from backend.app.services.embedding import EmbeddingError, EmbeddingInputTooLongError
from backend.app.services.hybrid import (
    HybridError,
    HybridResultError,
    HybridRetrievedChunk,
)
from backend.app.services.qdrant_store import (
    QdrantCollectionMismatchError,
    QdrantResultError,
    QdrantUnavailableError,
)


def hybrid_chunk(*, score: float = 0.032522) -> HybridRetrievedChunk:
    """Return one API-safe fused result."""
    return HybridRetrievedChunk(
        chunk_id=uuid4(),
        doc_id=uuid4(),
        chunk_index=0,
        content="VPN 故障请联系网络组，服务分机是 6203。",
        page=2,
        filename="policy.pdf",
        metadata={"token_count": 18},
        score=score,
        vector_rank=2,
        bm25_rank=1,
    )


class StubHybridService:
    """Record endpoint arguments and return controlled service behavior."""

    def __init__(
        self,
        *,
        results: list[HybridRetrievedChunk] | None = None,
        failure: BaseException | None = None,
    ) -> None:
        self.results = [] if results is None else results
        self.failure = failure
        self.calls: list[dict[str, Any]] = []

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        doc_id: UUID | None = None,
    ) -> list[HybridRetrievedChunk]:
        self.calls.append({"query": query, "top_k": top_k, "doc_id": doc_id})
        if self.failure is not None:
            raise self.failure
        return self.results


@pytest.fixture
def api_client() -> Iterator[tuple[TestClient, StubHybridService]]:
    """Provide the endpoint without resolving either real retrieval branch."""
    service = StubHybridService(results=[hybrid_chunk()])
    app.dependency_overrides[require_hybrid_retrieval_service] = lambda: service
    try:
        with TestClient(app) as client:
            yield client, service
    finally:
        app.dependency_overrides.clear()


def test_hybrid_api_returns_shared_payload_with_rrf_score(
    api_client: tuple[TestClient, StubHybridService],
) -> None:
    """The public shape stays shared while score represents RRF."""
    client, service = api_client

    response = client.post(
        "/retrieval/hybrid/search",
        json={"query": "  ＶＰＮ 6203  "},
    )

    assert response.status_code == 200
    assert service.calls == [{"query": "ＶＰＮ 6203", "top_k": 5, "doc_id": None}]
    assert response.json()["results"][0]["score"] == 0.032522
    assert "vector_rank" not in response.json()["results"][0]
    assert "bm25_rank" not in response.json()["results"][0]
    assert "vector_score" not in response.json()["results"][0]
    assert "bm25_score" not in response.json()["results"][0]


def test_hybrid_api_passes_top_k_and_doc_id(
    api_client: tuple[TestClient, StubHybridService],
) -> None:
    """The endpoint reuses the strict shared request contract."""
    client, service = api_client
    doc_id = uuid4()

    response = client.post(
        "/retrieval/hybrid/search",
        json={"query": "VPN", "top_k": 20, "doc_id": str(doc_id)},
    )

    assert response.status_code == 200
    assert service.calls[-1] == {"query": "VPN", "top_k": 20, "doc_id": doc_id}


def test_hybrid_api_returns_empty_results() -> None:
    """An empty union or unmatched valid filter is a successful search."""
    service = StubHybridService(results=[])
    app.dependency_overrides[require_hybrid_retrieval_service] = lambda: service
    try:
        with TestClient(app) as client:
            response = client.post(
                "/retrieval/hybrid/search",
                json={"query": "unknown", "doc_id": str(uuid4())},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"results": []}


@pytest.mark.parametrize(
    "payload",
    [
        {"query": "   "},
        {"query": "x" * 4097},
        {"query": "valid", "top_k": 0},
        {"query": "valid", "top_k": 21},
        {"query": "valid", "top_k": True},
        {"query": "valid", "top_k": "5"},
        {"query": "valid", "top_k": 5.0},
        {"query": "valid", "top_k": None},
        {"query": "valid", "doc_id": "not-a-uuid"},
        {"query": "valid", "candidate_k": 10},
        {"query": "valid", "rank_constant": 20},
        {"query": "valid", "mode": "hybrid"},
    ],
)
def test_hybrid_api_rejects_invalid_requests_before_service(
    api_client: tuple[TestClient, StubHybridService],
    payload: dict[str, Any],
) -> None:
    """Loose values and unapproved tuning fields never reach the service."""
    client, service = api_client

    response = client.post("/retrieval/hybrid/search", json=payload)

    assert response.status_code == 422
    assert service.calls == []


@pytest.mark.parametrize(
    ("failure", "expected_status", "expected_detail"),
    [
        (
            EmbeddingInputTooLongError(input_index=0, token_count=600, max_tokens=512),
            422,
            "The hybrid retrieval query exceeds the embedding model limit.",
        ),
        (
            EmbeddingError("private model path"),
            503,
            "The hybrid retrieval service is unavailable.",
        ),
        (
            QdrantUnavailableError("http://private-host:6333"),
            503,
            "The hybrid retrieval service is unavailable.",
        ),
        (
            QdrantCollectionMismatchError("wrong collection details"),
            503,
            "The hybrid retrieval service is unavailable.",
        ),
        (
            QdrantResultError("private vector payload"),
            502,
            "The hybrid retrieval service returned an invalid result.",
        ),
        (
            HybridResultError("private cross-store conflict"),
            502,
            "The hybrid retrieval service returned an invalid result.",
        ),
        (
            BM25UnavailableError("postgresql://private-host/database"),
            503,
            "The hybrid retrieval service is unavailable.",
        ),
        (
            BM25IndexError("private corpus content"),
            500,
            "The hybrid retrieval service failed.",
        ),
        (
            HybridError("private RRF state"),
            500,
            "The hybrid retrieval service failed.",
        ),
    ],
)
def test_hybrid_api_maps_failures_without_private_details(
    failure: BaseException,
    expected_status: int,
    expected_detail: str,
) -> None:
    """Branch and fusion failures retain their approved safe classifications."""
    service = StubHybridService(failure=failure)
    app.dependency_overrides[require_hybrid_retrieval_service] = lambda: service
    try:
        with TestClient(app) as client:
            response = client.post(
                "/retrieval/hybrid/search",
                json={"query": "VPN"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}
    assert str(failure) not in response.text


def test_health_does_not_resolve_hybrid_dependency() -> None:
    """Application startup and liveness stay independent of both branches."""
    resolved = False

    def fail_if_resolved() -> StubHybridService:
        nonlocal resolved
        resolved = True
        raise AssertionError("Hybrid dependency must remain lazy")

    app.dependency_overrides[require_hybrid_retrieval_service] = fail_if_resolved
    try:
        with TestClient(app) as client:
            response = client.get("/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert resolved is False


def test_openapi_exposes_independent_hybrid_route_without_tuning_fields() -> None:
    """Day 11 adds one route without changing the shared request model."""
    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()

    assert "/retrieval/hybrid/search" in schema["paths"]
    request = schema["components"]["schemas"]["RetrievalSearchRequest"]
    assert "candidate_k" not in request["properties"]
    assert "rank_constant" not in request["properties"]
    assert "mode" not in request["properties"]
