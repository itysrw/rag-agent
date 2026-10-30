"""Tests for complete and streamed Day 8 RAG chat responses."""

from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from backend.app.agent.service import PreparedRAGStream

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
from backend.app.services.bm25 import BM25IndexError, BM25UnavailableError
from backend.app.services.hybrid import HybridError, HybridResultError
from backend.app.services.reranker import (
    RerankedChunk, RerankOutcome, RerankerInputError, RerankerResultError,
    RerankerUnavailableError,
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

    def complete(self, question: str) -> RAGAnswer:
        prepared = self.prepare(question)
        if self.complete_failure is not None:
            raise self.complete_failure
        if not prepared.has_relevant_context:
            return RAGAnswer(NO_RELEVANT_KNOWLEDGE, self.model, ())
        return RAGAnswer("reply:hello", self.model, prepared.sources)

    def start_stream(self, question: str) -> PreparedRAGStream:
        return PreparedRAGStream(iter(()), prepared=self.prepare(question))

    def stream(self, run: PreparedRAGStream) -> Iterator[str]:
        prepared = run.prepared
        assert prepared is not None
        if not prepared.has_relevant_context:
            yield NO_RELEVANT_KNOWLEDGE
            return
        yield "reply:"
        if self.stream_failure is not None:
            raise self.stream_failure
        yield "hello"


class FixedRetrievalService:
    """Return one trusted source without contacting Embedding or Qdrant."""

    def search(self, question: str) -> RerankOutcome:
        del question
        return RerankOutcome((
            RerankedChunk(
                chunk_id=uuid4(),
                doc_id=uuid4(),
                chunk_index=0,
                content="trusted context",
                page=1,
                filename="real.pdf",
                metadata={},
                score=0.9,
                hybrid_score=0.02, hybrid_rank=1, rerank_rank=1, rank_change=0,
                vector_score=0.9, vector_rank=1, bm25_rank=1,
            )
        ,), (), 1, 0)


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
        (BM25UnavailableError("private database"), 503, "The retrieval service is unavailable."),
        (BM25IndexError("private index"), 500, "The retrieval service failed."),
        (HybridError("private fusion"), 500, "The retrieval service failed."),
        (HybridResultError("private conflict"), 502, "The retrieval service returned an invalid result."),
        (RerankerUnavailableError("private model"), 503, "The retrieval service is unavailable."),
        (RerankerResultError("private scores"), 502, "The retrieval service returned an invalid result."),
        (RerankerInputError("private query"), 422, "The chat message exceeds the reranker model limit."),
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


@pytest.mark.parametrize("stream", [False, True])
@pytest.mark.parametrize(("failure", "status"), [
    (RerankerInputError("private-retrieval"), 422),
    (BM25IndexError("private-retrieval"), 500),
    (HybridResultError("private-retrieval"), 502),
    (RerankerUnavailableError("private-retrieval"), 503),
])
def test_real_graph_keeps_retrieval_http_errors_before_sse(
    stream: bool, failure: BaseException, status: int,
) -> None:
    from backend.tests.test_rag import StubLLMClient
    class BrokenRetrieval:
        def search(self, question: str) -> RerankOutcome:
            raise failure
    llm = StubLLMClient()
    service = RAGService(BrokenRetrieval(), llm, RAGSettings(_env_file=None))
    app.dependency_overrides[require_rag_service] = lambda: service
    try:
        with TestClient(app) as client:
            response = client.post("/chat", json={"message": "private-query", "stream": stream})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/json")
    assert "event:" not in response.text and "private-" not in response.text
    assert llm.complete_calls == llm.stream_calls == []


def test_public_chat_schema_and_input_cannot_disable_retrieval() -> None:
    from backend.tests.test_rag import StubLLMClient, StubRetrievalService
    retrieval = StubRetrievalService([])
    service = RAGService(retrieval, StubLLMClient(), RAGSettings(_env_file=None))
    app.dependency_overrides[require_rag_service] = lambda: service
    try:
        with TestClient(app) as client:
            schema = client.get("/openapi.json").json()
            assert set(schema["components"]["schemas"]["ChatRequest"]["properties"]) == {"message", "stream"}
            response = client.post("/chat", json={"message": "question", "needs_retrieval": False})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == {"answer": NO_RELEVANT_KNOWLEDGE, "model": "test-model", "sources": []}
    assert retrieval.questions == ["question"]


def test_asgi_disconnect_closes_prefetched_graph_and_upstream() -> None:
    import anyio
    from typing import Any
    from backend.tests.test_agent_service import TrackingLLM
    from backend.tests.test_rag import StubRetrievalService, retrieved_chunk
    llm = TrackingLLM()
    service = RAGService(
        StubRetrievalService([retrieved_chunk(score=0.9)]), llm, RAGSettings(_env_file=None)
    )
    response = chat_module.chat(chat_module.ChatRequest(message="question", stream=True), service)
    bodies: list[bytes] = []
    async def invoke() -> None:
        sent = anyio.Event()
        async def receive() -> dict[str, str]:
            await sent.wait()
            return {"type": "http.disconnect"}
        async def send(message: Any) -> None:
            if message["type"] == "http.response.body" and message.get("body"):
                bodies.append(message["body"])
                sent.set()
                await anyio.sleep(0)
        await response({
            "type": "http", "method": "POST", "path": "/chat",
            "asgi": {"version": "3.0", "spec_version": "2.0"},
            "headers": [],
        }, receive, send)
    anyio.run(invoke, backend="asyncio")
    assert bodies and b"delta" in bodies[0]
    assert b"event: sources" not in b"".join(bodies)
    assert b"[DONE]" not in b"".join(bodies)
    assert response._run.closed
    assert llm.closed == 1


@pytest.mark.parametrize("stream", [False, True])
def test_graph_llm_failure_keeps_error_contract_without_logging_state(stream: bool) -> None:
    from typing import Any
    from loguru import logger
    class BrokenLLM:
        model = "test-model"
        def complete_messages(self, messages: Any) -> str:
            raise LLMServiceError("private-upstream")
        def stream_messages(self, messages: Any) -> Iterator[str]:
            yield "visible"
            raise LLMServiceError("private-upstream")
    service = RAGService(FixedRetrievalService(), BrokenLLM(), RAGSettings(_env_file=None))
    app.dependency_overrides[require_rag_service] = lambda: service
    logs: list[str] = []
    handler = logger.add(lambda message: logs.append(str(message)))
    try:
        with TestClient(app) as client:
            response = client.post("/chat", json={"message": "private-question", "stream": stream})
    finally:
        app.dependency_overrides.clear()
        logger.remove(handler)
    if stream:
        assert response.status_code == 200 and "event: error" in response.text
        assert "event: sources" not in response.text and "[DONE]" not in response.text
    else:
        assert response.status_code == 502
        assert response.json() == {"detail": "The language model request failed."}
    for forbidden in ("private-question", "private-upstream", "trusted context", "system rules"):
        assert forbidden not in response.text
        assert forbidden not in "".join(logs)
