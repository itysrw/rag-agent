"""HTTP and fixed-pipeline tests without model downloads or external services."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from backend.app.api.rerank import require_reranked_retrieval_service
from backend.app.main import app
from backend.app.services.bm25 import BM25IndexError, BM25UnavailableError
from backend.app.services.embedding import EmbeddingError, EmbeddingInputTooLongError
from backend.app.services.hybrid import HybridError, HybridResultError
from backend.app.services.qdrant_store import QdrantResultError, QdrantUnavailableError
from backend.app.services.reranker import (
    RerankedRetrievalService, RerankerInputError, RerankerResultError,
    RerankerUnavailableError,
)
from backend.tests.test_reranker import FakeModel, candidates, service


@pytest.fixture
def api_client() -> Iterator[tuple[TestClient, list[Any]]]:
    """Use the production orchestration and model adapter with fake IO."""
    calls: list[Any] = []
    class Hybrid:
        def search(self, query: str, **kwargs: Any) -> Any:
            calls.append((query, kwargs))
            return candidates()
    pipeline = RerankedRetrievalService(Hybrid(), service(FakeModel()))  # type: ignore[arg-type]
    app.dependency_overrides[require_reranked_retrieval_service] = lambda: pipeline
    try:
        with TestClient(app) as client:
            yield client, calls
    finally:
        app.dependency_overrides.clear()


def test_endpoint_scores_twenty_and_returns_five_with_rank_changes(api_client: Any) -> None:
    client, calls = api_client
    response = client.post("/retrieval/rerank/search", json={"query": "  VPN  ", "doc_id": str(UUID(int=100))})
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 5
    assert calls == [("VPN", {"top_k": 20, "doc_id": UUID(int=100)})]
    assert results[0]["hybrid_rank"] == 20
    assert results[0]["rerank_rank"] == 1
    assert results[0]["rank_change"] == 19
    assert results[0]["score"] == 19.0
    assert results[0]["chunk_id"] == str(UUID(int=20))
    for field in ("hybrid_score", "vector_score", "bm25_score", "vector_rank", "bm25_rank"):
        assert field not in results[0]


@pytest.mark.parametrize("payload", [
    {"query": "  "}, {"query": "x"*4097}, {"query": "VPN", "top_k": 5},
    {"query": "VPN", "candidate_k": 20}, {"query": "VPN", "mode": "rerank"},
    {"query": "VPN", "doc_id": "bad"}, {"query": "VPN", "doc_id": [str(UUID(int=1))]},
])
def test_invalid_requests_do_not_call_hybrid(api_client: Any, payload: Any) -> None:
    client, calls = api_client
    assert client.post("/retrieval/rerank/search", json=payload).status_code == 422
    assert calls == []


@pytest.mark.parametrize(("failure", "status"), [
    (EmbeddingInputTooLongError(token_count=600, max_tokens=512), 422),
    (RerankerInputError("private-query"), 422),
    (EmbeddingError("private-model"), 503),
    (QdrantUnavailableError("private-host"), 503),
    (BM25UnavailableError("private-database"), 503),
    (RerankerUnavailableError("private-cache"), 503),
    (QdrantResultError("private-payload"), 502),
    (HybridResultError("private-conflict"), 502),
    (RerankerResultError("private-output"), 502),
    (BM25IndexError("private-index"), 500),
    (HybridError("private-fusion"), 500),
])
def test_safe_failure_mapping(failure: BaseException, status: int) -> None:
    class Broken:
        def search(self, *args: Any, **kwargs: Any) -> Any:
            raise failure
    app.dependency_overrides[require_reranked_retrieval_service] = Broken
    try:
        with TestClient(app) as client:
            response = client.post("/retrieval/rerank/search", json={"query": "question"})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == status
    assert str(failure) not in response.text


def test_openapi_has_no_client_tuning_fields() -> None:
    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()
    request = schema["components"]["schemas"]["RerankSearchRequest"]
    assert set(request["properties"]) == {"query", "doc_id"}
    assert request["additionalProperties"] is False
