"""HTTP contract tests for the independent Day 10 BM25 endpoint."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from backend.app.api.bm25 import require_bm25_service
from backend.app.main import app
from backend.app.services.bm25 import (
    BM25IndexError,
    BM25RetrievedChunk,
    BM25UnavailableError,
)


def retrieved_chunk(*, score: float = 2.73) -> BM25RetrievedChunk:
    """Return one API-safe raw BM25 result."""
    return BM25RetrievedChunk(
        chunk_id=uuid4(),
        doc_id=uuid4(),
        chunk_index=0,
        content="VPN 故障请联系网络组，服务分机是 6203。",
        page=2,
        filename="policy.pdf",
        metadata={"token_count": 18},
        score=score,
    )


class StubBM25Service:
    """Record endpoint arguments and return controlled service behavior."""

    def __init__(
        self,
        *,
        results: list[BM25RetrievedChunk] | None = None,
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
    ) -> list[BM25RetrievedChunk]:
        self.calls.append({"query": query, "top_k": top_k, "doc_id": doc_id})
        if self.failure is not None:
            raise self.failure
        return self.results


@pytest.fixture
def api_client() -> Iterator[tuple[TestClient, StubBM25Service]]:
    """Provide the endpoint without PostgreSQL access."""
    service = StubBM25Service(results=[retrieved_chunk()])
    app.dependency_overrides[require_bm25_service] = lambda: service
    try:
        with TestClient(app) as client:
            yield client, service
    finally:
        app.dependency_overrides.clear()


def test_bm25_api_returns_shared_payload_with_unbounded_raw_score(
    api_client: tuple[TestClient, StubBM25Service],
) -> None:
    """The response matches vector retrieval without constraining BM25 score."""
    client, service = api_client

    response = client.post(
        "/retrieval/bm25/search",
        json={"query": "  ＶＰＮ 6203  "},
    )

    assert response.status_code == 200
    assert service.calls == [{"query": "ＶＰＮ 6203", "top_k": 5, "doc_id": None}]
    assert response.json()["results"][0]["score"] == 2.73
    assert "vector" not in response.json()["results"][0]


def test_bm25_api_passes_top_k_and_doc_id(
    api_client: tuple[TestClient, StubBM25Service],
) -> None:
    """Day 9 request controls are reused without a mode parameter."""
    client, service = api_client
    doc_id = uuid4()

    response = client.post(
        "/retrieval/bm25/search",
        json={"query": "VPN", "top_k": 20, "doc_id": str(doc_id)},
    )

    assert response.status_code == 200
    assert service.calls[-1] == {"query": "VPN", "top_k": 20, "doc_id": doc_id}


def test_bm25_api_returns_empty_results() -> None:
    """Empty corpus, no overlap, and unknown filters share the 200 empty shape."""
    service = StubBM25Service(results=[])
    app.dependency_overrides[require_bm25_service] = lambda: service
    try:
        with TestClient(app) as client:
            response = client.post(
                "/retrieval/bm25/search",
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
        {"query": "valid", "mode": "bm25"},
    ],
)
def test_bm25_api_rejects_invalid_requests_before_service(
    api_client: tuple[TestClient, StubBM25Service],
    payload: dict[str, Any],
) -> None:
    """The endpoint exactly reuses Day 9's strict request validation."""
    client, service = api_client

    response = client.post("/retrieval/bm25/search", json=payload)

    assert response.status_code == 422
    assert service.calls == []


@pytest.mark.parametrize(
    ("failure", "expected_status", "expected_detail"),
    [
        (
            BM25UnavailableError("postgresql://secret-host/private"),
            503,
            "The BM25 retrieval service is unavailable.",
        ),
        (
            BM25IndexError("private corpus content"),
            500,
            "The BM25 retrieval service failed.",
        ),
    ],
)
def test_bm25_api_maps_failures_without_private_details(
    failure: BaseException,
    expected_status: int,
    expected_detail: str,
) -> None:
    """Database and index failures expose only the approved contract."""
    service = StubBM25Service(failure=failure)
    app.dependency_overrides[require_bm25_service] = lambda: service
    try:
        with TestClient(app) as client:
            response = client.post(
                "/retrieval/bm25/search",
                json={"query": "VPN"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}
    assert str(failure) not in response.text


def test_health_does_not_resolve_bm25_dependency() -> None:
    """Application startup and liveness remain independent of PostgreSQL."""
    resolved = False

    def fail_if_resolved() -> StubBM25Service:
        nonlocal resolved
        resolved = True
        raise AssertionError("BM25 dependency must remain lazy")

    app.dependency_overrides[require_bm25_service] = fail_if_resolved
    try:
        with TestClient(app) as client:
            response = client.get("/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert resolved is False


def test_openapi_exposes_only_the_independent_bm25_route() -> None:
    """Day 10 adds its route without a Hybrid mode on vector retrieval."""
    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()

    assert "/retrieval/bm25/search" in schema["paths"]
    vector_request = schema["components"]["schemas"]["RetrievalSearchRequest"]
    assert "mode" not in vector_request["properties"]
