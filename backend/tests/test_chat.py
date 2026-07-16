"""Tests for complete and streamed Day 8 RAG chat responses."""

from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.app.api import chat as chat_module
from backend.app.api.chat import require_rag_service
from backend.app.core.config import RAGSettings
from backend.app.main import app
from backend.app.services.embedding import (
    EmbeddingError,
    EmbeddingInputTooLongError,
)
from backend.app.services.llm import (
    LLMConfigurationError,
    LLMMessage,
    LLMServiceError,
)
from backend.app.services.qdrant_store import (
    QdrantCollectionMismatchError,
    QdrantResultError,
    QdrantUnavailableError,
    RetrievedChunk,
)
from backend.app.services.rag import (
    NO_RELEVANT_KNOWLEDGE,
    PreparedRAG,
    RAGAnswer,
    RAGService,
    RAGSource,
)

FABRICATED_REFERENCE = "[fake.pdf page 99] [S99]"
FABRICATED_REFERENCE_MARKERS = ("fake.pdf", "page 99", "[S99]")


def relevant_prepared(question: str = "hello") -> PreparedRAG:
    """Return one safely prepared request with a backend-derived source."""
    source = RAGSource(filename="policy.pdf", page=1)
    return PreparedRAG(
        question=question,
        messages=(
            {"role": "system", "content": "rules"},
            {"role": "user", "content": question},
        ),
        sources=(source,),
        has_relevant_context=True,
    )


def refused_prepared(question: str = "hello") -> PreparedRAG:
    """Return a prepared request that must bypass the language model."""
    return PreparedRAG(
        question=question,
        messages=(),
        sources=(),
        has_relevant_context=False,
    )


class StubRAGService:
    """Deterministic RAG replacement for the HTTP contract."""

    model = "test-model"

    def __init__(
        self,
        *,
        prepared: PreparedRAG | None = None,
        prepare_failure: BaseException | None = None,
        complete_failure: BaseException | None = None,
        stream_failure: BaseException | None = None,
    ) -> None:
        self.prepared = prepared or relevant_prepared()
        self.prepare_failure = prepare_failure
        self.complete_failure = complete_failure
        self.stream_failure = stream_failure
        self.questions: list[str] = []

    def prepare(self, question: str) -> PreparedRAG:
        self.questions.append(question)
        if self.prepare_failure is not None:
            raise self.prepare_failure
        return self.prepared

    def complete(self, prepared: PreparedRAG) -> RAGAnswer:
        if self.complete_failure is not None:
            raise self.complete_failure
        if not prepared.has_relevant_context:
            return RAGAnswer(NO_RELEVANT_KNOWLEDGE, self.model, ())
        return RAGAnswer("reply:hello", self.model, prepared.sources)

    def stream(self, prepared: PreparedRAG) -> Iterator[str]:
        if not prepared.has_relevant_context:
            yield NO_RELEVANT_KNOWLEDGE
            return
        yield "reply:"
        if self.stream_failure is not None:
            raise self.stream_failure
        yield "hello"


class FixedRetrievalService:
    """Return one trusted source without contacting Embedding or Qdrant."""

    def search(self, question: str) -> list[RetrievedChunk]:
        del question
        return [
            RetrievedChunk(
                chunk_id=uuid4(),
                doc_id=uuid4(),
                chunk_index=0,
                content="trusted context",
                page=1,
                filename="real.pdf",
                metadata={},
                score=0.9,
            )
        ]


class FabricatingLLMClient:
    """Return a source reference that is absent from the trusted Context."""

    model = "test-model"

    def complete_messages(self, messages: Sequence[LLMMessage]) -> str:
        del messages
        return f"Supported answer. {FABRICATED_REFERENCE}"

    def stream_messages(self, messages: Sequence[LLMMessage]) -> Iterator[str]:
        del messages
        yield "Supported answer. [fa"
        yield "ke.pdf page "
        yield "99] [S"
        yield "99]"


@pytest.fixture
def api_client() -> Iterator[tuple[TestClient, StubRAGService]]:
    """Provide an API client with retrieval and generation replaced."""
    service = StubRAGService()
    app.dependency_overrides[require_rag_service] = lambda: service
    try:
        with TestClient(app) as test_client:
            yield test_client, service
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def fabricated_reference_api_client() -> Iterator[TestClient]:
    """Use the real RAG service with controlled retrieval and model output."""
    service = RAGService(
        FixedRetrievalService(),  # type: ignore[arg-type]
        FabricatingLLMClient(),  # type: ignore[arg-type]
        RAGSettings(_env_file=None),
    )
    app.dependency_overrides[require_rag_service] = lambda: service
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def test_chat_returns_complete_rag_response(
    api_client: tuple[TestClient, StubRAGService],
) -> None:
    """Non-streaming chat trims input and returns structured sources."""
    client, service = api_client

    response = client.post("/chat", json={"message": "  hello  "})

    assert response.status_code == 200
    assert service.questions == ["hello"]
    assert response.json() == {
        "answer": "reply:hello",
        "model": "test-model",
        "sources": [{"filename": "policy.pdf", "page": 1}],
    }


def test_chat_returns_sse_deltas_sources_and_done(
    api_client: tuple[TestClient, StubRAGService],
) -> None:
    """Successful streams finish with sources followed by DONE."""
    client, _ = api_client

    with client.stream(
        "POST",
        "/chat",
        json={"message": "hello", "stream": True},
    ) as response:
        body = response.read().decode("utf-8")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert body.split("\n\n") == [
        'data: {"delta": "reply:"}',
        'data: {"delta": "hello"}',
        'event: sources\ndata: {"sources": [{"filename": "policy.pdf", "page": 1}]}',
        "data: [DONE]",
        "",
    ]


def test_chat_complete_does_not_expose_model_fabricated_source_reference(
    fabricated_reference_api_client: TestClient,
) -> None:
    """The complete HTTP answer only exposes backend-controlled sources."""
    response = fabricated_reference_api_client.post(
        "/chat",
        json={"message": "question"},
    )

    assert response.status_code == 200
    body = response.json()
    for marker in FABRICATED_REFERENCE_MARKERS:
        assert marker not in body["answer"]
    assert body["sources"] == [{"filename": "real.pdf", "page": 1}]


def test_chat_sse_does_not_expose_model_fabricated_source_reference(
    fabricated_reference_api_client: TestClient,
) -> None:
    """The reconstructed SSE answer only exposes backend-controlled sources."""
    with fabricated_reference_api_client.stream(
        "POST",
        "/chat",
        json={"message": "question", "stream": True},
    ) as response:
        body = response.read().decode("utf-8")

    deltas = []
    for event in body.split("\n\n"):
        if event.startswith("data: {"):
            payload = json.loads(event.removeprefix("data: "))
            if "delta" in payload:
                deltas.append(payload["delta"])
    streamed_answer = "".join(deltas)

    assert response.status_code == 200
    for marker in FABRICATED_REFERENCE_MARKERS:
        assert marker not in streamed_answer
    assert (
        'event: sources\ndata: {"sources": [{"filename": "real.pdf", "page": 1}]}'
        in body
    )


@pytest.mark.parametrize("stream", [False, True])
def test_chat_refuses_without_context_and_returns_no_sources(stream: bool) -> None:
    """The fixed refusal works in both modes without fabricated sources."""
    service = StubRAGService(prepared=refused_prepared())
    app.dependency_overrides[require_rag_service] = lambda: service
    try:
        with TestClient(app) as client:
            response = client.post(
                "/chat",
                json={"message": "outside knowledge", "stream": stream},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    if not stream:
        assert response.json() == {
            "answer": NO_RELEVANT_KNOWLEDGE,
            "model": "test-model",
            "sources": [],
        }
    else:
        assert response.text.split("\n\n") == [
            f'data: {{"delta": "{NO_RELEVANT_KNOWLEDGE}"}}',
            'event: sources\ndata: {"sources": []}',
            "data: [DONE]",
            "",
        ]


def test_chat_rejects_blank_message(
    api_client: tuple[TestClient, StubRAGService],
) -> None:
    """Whitespace-only user messages fail before retrieval."""
    client, service = api_client

    response = client.post("/chat", json={"message": "   "})

    assert response.status_code == 422
    assert service.questions == []


def test_chat_rejects_message_over_character_limit_before_rag(
    api_client: tuple[TestClient, StubRAGService],
) -> None:
    """A 4097-character message fails before retrieval or tokenization."""
    client, service = api_client

    response = client.post("/chat", json={"message": "x" * 4097})

    assert response.status_code == 422
    assert service.questions == []


def test_chat_returns_503_without_llm_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing API key fails safely while resolving the RAG service."""
    def missing_service() -> StubRAGService:
        raise LLMConfigurationError("missing key")

    app.dependency_overrides.clear()
    monkeypatch.setattr(chat_module, "get_rag_service", missing_service)

    with TestClient(app) as client:
        response = client.post("/chat", json={"message": "hello"})

    assert response.status_code == 503
    assert response.json() == {"detail": "The language model is not configured."}


@pytest.mark.parametrize(
    ("failure", "expected_status", "expected_detail"),
    [
        (
            EmbeddingInputTooLongError(token_count=600, max_tokens=512),
            422,
            "The chat message exceeds the embedding model limit.",
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
            QdrantCollectionMismatchError("private collection"),
            503,
            "The retrieval service is unavailable.",
        ),
        (
            QdrantResultError("private payload"),
            502,
            "The retrieval service returned an invalid result.",
        ),
    ],
)
def test_chat_maps_retrieval_failures_before_streaming(
    failure: BaseException,
    expected_status: int,
    expected_detail: str,
) -> None:
    """Retrieval failures retain HTTP status because prepare runs first."""
    service = StubRAGService(prepare_failure=failure)
    app.dependency_overrides[require_rag_service] = lambda: service
    try:
        with TestClient(app) as client:
            response = client.post(
                "/chat",
                json={"message": "hello", "stream": True},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}
    assert str(failure) not in response.text


def test_chat_maps_complete_failure_to_502() -> None:
    """A generation failure before a JSON answer becomes HTTP 502."""
    service = StubRAGService(complete_failure=LLMServiceError("private prompt"))
    app.dependency_overrides[require_rag_service] = lambda: service
    try:
        with TestClient(app) as client:
            response = client.post("/chat", json={"message": "hello"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json() == {"detail": "The language model request failed."}
    assert "private prompt" not in response.text


def test_chat_sends_error_without_sources_or_done_after_stream_failure() -> None:
    """A started failed stream terminates with only a safe error event."""
    service = StubRAGService(stream_failure=LLMServiceError("private prompt"))
    app.dependency_overrides[require_rag_service] = lambda: service
    try:
        with TestClient(app) as client:
            with client.stream(
                "POST",
                "/chat",
                json={"message": "hello", "stream": True},
            ) as response:
                body = response.read().decode("utf-8")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert body.split("\n\n") == [
        'data: {"delta": "reply:"}',
        'event: error\ndata: {"detail": "The language model stream failed."}',
        "",
    ]
    assert "sources" not in body
    assert "[DONE]" not in body


def test_health_does_not_resolve_rag_dependency() -> None:
    """Application startup and liveness remain independent of RAG services."""
    resolved = False

    def fail_if_resolved() -> StubRAGService:
        nonlocal resolved
        resolved = True
        raise AssertionError("RAG dependency must remain lazy")

    app.dependency_overrides[require_rag_service] = fail_if_resolved
    try:
        with TestClient(app) as client:
            response = client.get("/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert resolved is False
