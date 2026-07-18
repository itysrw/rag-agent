"""Tests for tunable retrieval orchestration, logging, and HTTP mapping."""

from __future__ import annotations

import hashlib
import json
import sys
from collections.abc import Iterator
from io import StringIO
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from loguru import logger

from backend.app.api.retrieval import require_retrieval_service
from backend.app.core.logging import configure_logging
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
from backend.app.services.retrieval import (
    RETRIEVAL_SEARCH_EVENT,
    RETRIEVAL_TOP_K,
    RETRIEVAL_TOP_K_MAX,
    RETRIEVAL_TOP_K_MIN,
    RetrievalService,
)


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
    """Record search arguments and return controlled results."""

    def __init__(self, results: list[RetrievedChunk] | None = None) -> None:
        self.results = results or []
        self.calls: list[dict[str, Any]] = []

    def search(
        self,
        query_vector: tuple[float, ...],
        *,
        limit: int,
        doc_id: UUID | None = None,
    ) -> list[RetrievedChunk]:
        self.calls.append(
            {"query_vector": query_vector, "limit": limit, "doc_id": doc_id}
        )
        return self.results


def retrieved_chunk(score: float = 0.91) -> RetrievedChunk:
    """Return one complete API-safe retrieval result."""
    return RetrievedChunk(
        chunk_id=uuid4(),
        doc_id=uuid4(),
        chunk_index=0,
        content="报销票据每月二十五日前提交。",
        page=1,
        filename="policy.pdf",
        metadata={"token_count": 12},
        score=score,
    )


@pytest.fixture
def captured_logs() -> Iterator[list[str]]:
    """Capture raw Loguru messages emitted during one test."""
    messages: list[str] = []
    handler_id = logger.add(
        lambda message: messages.append(message.record["message"]),
        level="INFO",
    )
    try:
        yield messages
    finally:
        logger.remove(handler_id)


def search_events(messages: list[str]) -> list[dict[str, Any]]:
    """Return every parsed retrieval search event among raw log messages."""
    events: list[dict[str, Any]] = []
    for message in messages:
        try:
            data = json.loads(message)
        except ValueError:
            continue
        if isinstance(data, dict) and data.get("event") == RETRIEVAL_SEARCH_EVENT:
            events.append(data)
    return events


def test_retrieval_service_defaults_to_fixed_top_five() -> None:
    """Day 8 callers keep the Day 7 fixed limit without new arguments."""
    embedding = StubEmbeddingClient()
    vector_store = StubVectorStore([retrieved_chunk()])
    service = RetrievalService(embedding, vector_store)  # type: ignore[arg-type]

    results = service.search("报销时间")

    assert len(results) == 1
    assert embedding.queries == ["报销时间"]
    assert vector_store.calls == [
        {"query_vector": basis_vector(), "limit": RETRIEVAL_TOP_K, "doc_id": None}
    ]
    assert RETRIEVAL_TOP_K == 5
    assert (RETRIEVAL_TOP_K_MIN, RETRIEVAL_TOP_K_MAX) == (1, 20)


def test_retrieval_service_passes_top_k_and_doc_id_through() -> None:
    """Day 9 arguments reach the vector store without modification."""
    embedding = StubEmbeddingClient()
    vector_store = StubVectorStore([retrieved_chunk()])
    service = RetrievalService(embedding, vector_store)  # type: ignore[arg-type]
    doc_id = uuid4()

    service.search("报销时间", top_k=20, doc_id=doc_id)

    assert vector_store.calls == [
        {"query_vector": basis_vector(), "limit": 20, "doc_id": doc_id}
    ]


@pytest.mark.parametrize(
    "top_k",
    [0, -1, 21, True, False, "5", 5.0, None],
)
def test_retrieval_service_rejects_invalid_top_k_before_embedding(
    top_k: Any,
) -> None:
    """A direct caller cannot spend embedding work on an invalid limit."""
    embedding = StubEmbeddingClient()
    vector_store = StubVectorStore([retrieved_chunk()])
    service = RetrievalService(embedding, vector_store)  # type: ignore[arg-type]

    with pytest.raises(ValueError):
        service.search("报销时间", top_k=top_k)

    assert embedding.queries == []
    assert vector_store.calls == []


def test_retrieval_service_logs_one_safe_json_event(
    captured_logs: list[str],
) -> None:
    """One successful search emits exactly one machine-readable event."""
    high = retrieved_chunk(score=0.91)
    low = retrieved_chunk(score=0.44)
    embedding = StubEmbeddingClient()
    vector_store = StubVectorStore([high, low])
    service = RetrievalService(embedding, vector_store)  # type: ignore[arg-type]
    doc_id = uuid4()

    service.search("报销时间", top_k=3, doc_id=doc_id)

    events = search_events(captured_logs)
    assert len(events) == 1
    event = events[0]
    assert event["query_sha256"] == hashlib.sha256(
        "报销时间".encode("utf-8")
    ).hexdigest()
    assert event["query_len"] == 4
    assert event["top_k"] == 3
    assert event["filter_doc_id"] == str(doc_id)
    assert event["result_count"] == 2
    assert event["results"] == [
        {
            "rank": 1,
            "chunk_id": str(high.chunk_id),
            "doc_id": str(high.doc_id),
            "filename": "policy.pdf",
            "page": 1,
            "score": 0.91,
        },
        {
            "rank": 2,
            "chunk_id": str(low.chunk_id),
            "doc_id": str(low.doc_id),
            "filename": "policy.pdf",
            "page": 1,
            "score": 0.44,
        },
    ]


def test_retrieval_search_log_excludes_query_content_and_metadata(
    captured_logs: list[str],
) -> None:
    """The event is one line and never carries raw query or chunk text."""
    embedding = StubEmbeddingClient()
    vector_store = StubVectorStore([retrieved_chunk()])
    service = RetrievalService(embedding, vector_store)  # type: ignore[arg-type]

    service.search("报销时间")

    raw_events = [
        message for message in captured_logs if RETRIEVAL_SEARCH_EVENT in message
    ]
    assert len(raw_events) == 1
    raw = raw_events[0]
    assert "\n" not in raw
    assert "报销时间" not in raw
    assert "报销票据每月二十五日前提交。" not in raw
    assert '"content"' not in raw
    assert '"metadata"' not in raw
    assert '"vector"' not in raw
    assert '"query"' not in raw


def test_retrieval_service_logs_empty_result_event(
    captured_logs: list[str],
) -> None:
    """A successful search without matches still emits one event."""
    embedding = StubEmbeddingClient()
    vector_store = StubVectorStore([])
    service = RetrievalService(embedding, vector_store)  # type: ignore[arg-type]

    results = service.search("报销时间")

    assert results == []
    events = search_events(captured_logs)
    assert len(events) == 1
    assert events[0]["result_count"] == 0
    assert events[0]["results"] == []
    assert events[0]["filter_doc_id"] is None


def test_retrieval_logging_sink_emits_directly_parseable_json_line(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The complete application-formatted retrieval line is valid JSONL."""
    output = StringIO()
    original_stderr = sys.stderr
    monkeypatch.setattr(sys, "stderr", output)
    configure_logging(debug=False)
    try:
        service = RetrievalService(  # type: ignore[arg-type]
            StubEmbeddingClient(),
            StubVectorStore([]),
        )

        service.search("报销时间")

        event_lines = [
            line
            for line in output.getvalue().splitlines()
            if RETRIEVAL_SEARCH_EVENT in line
        ]
    finally:
        monkeypatch.setattr(sys, "stderr", original_stderr)
        configure_logging(debug=False)

    assert len(event_lines) == 1
    event = json.loads(event_lines[0])
    assert event["event"] == RETRIEVAL_SEARCH_EVENT


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
        self.calls: list[dict[str, Any]] = []

    def search(
        self,
        query: str,
        *,
        top_k: int = RETRIEVAL_TOP_K,
        doc_id: UUID | None = None,
    ) -> list[RetrievedChunk]:
        self.queries.append(query)
        self.calls.append({"query": query, "top_k": top_k, "doc_id": doc_id})
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


def test_search_api_defaults_to_top_five_without_filter(
    api_client: tuple[TestClient, StubRetrievalService],
) -> None:
    """A Day 7-shaped request keeps the fixed limit and no document filter."""
    client, service = api_client

    response = client.post("/retrieval/search", json={"query": "报销时间"})

    assert response.status_code == 200
    assert service.calls == [
        {"query": "报销时间", "top_k": RETRIEVAL_TOP_K, "doc_id": None}
    ]


@pytest.mark.parametrize("top_k", [1, 20])
def test_search_api_accepts_top_k_bounds(
    api_client: tuple[TestClient, StubRetrievalService],
    top_k: int,
) -> None:
    """Both inclusive bounds of the documented range are usable."""
    client, service = api_client

    response = client.post(
        "/retrieval/search", json={"query": "报销时间", "top_k": top_k}
    )

    assert response.status_code == 200
    assert service.calls[-1]["top_k"] == top_k


def test_search_api_passes_doc_id_filter_to_service(
    api_client: tuple[TestClient, StubRetrievalService],
) -> None:
    """A valid document filter reaches the service as one UUID."""
    client, service = api_client
    doc_id = uuid4()

    response = client.post(
        "/retrieval/search",
        json={"query": "报销时间", "top_k": 8, "doc_id": str(doc_id)},
    )

    assert response.status_code == 200
    assert service.calls == [{"query": "报销时间", "top_k": 8, "doc_id": doc_id}]


def test_search_api_accepts_explicit_null_doc_id(
    api_client: tuple[TestClient, StubRetrievalService],
) -> None:
    """An explicit null filter behaves exactly like an absent filter."""
    client, service = api_client

    response = client.post(
        "/retrieval/search", json={"query": "报销时间", "doc_id": None}
    )

    assert response.status_code == 200
    assert service.calls[-1]["doc_id"] is None


def test_search_api_returns_empty_results_for_unmatched_doc_id() -> None:
    """A valid filter without matches is a successful empty retrieval."""
    service = StubRetrievalService(results=[])
    app.dependency_overrides[require_retrieval_service] = lambda: service
    try:
        with TestClient(app) as client:
            response = client.post(
                "/retrieval/search",
                json={"query": "报销时间", "doc_id": str(uuid4())},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"results": []}


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
        {"query": "valid", "limit": 3},
        {"query": "valid", "top_k": 0},
        {"query": "valid", "top_k": 21},
        {"query": "valid", "top_k": -1},
        {"query": "valid", "top_k": True},
        {"query": "valid", "top_k": "5"},
        {"query": "valid", "top_k": 5.0},
        {"query": "valid", "top_k": None},
        {"query": "valid", "doc_id": "not-a-uuid"},
        {"query": "valid", "doc_id": 12345},
    ],
)
def test_search_api_rejects_invalid_request_fields(
    api_client: tuple[TestClient, StubRetrievalService],
    payload: dict[str, Any],
) -> None:
    """Blank queries, unknown fields, and loose types never reach the service."""
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
