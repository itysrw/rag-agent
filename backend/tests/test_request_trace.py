"""Day 19 request trace evidence through the production chat graph."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
import json
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import anyio
from fastapi.testclient import TestClient
from loguru import logger
import pytest
from sqlalchemy.exc import IntegrityError

from backend.app.api.chat import ChatRequest, chat, require_rag_service
from backend.app.core.config import RAGSettings
from backend.app.main import app
from backend.app.models.request_log import RequestLog
from backend.app.services.conversation_memory import ConversationMemoryError
from backend.app.services.llm import AgentToolCall, LLMClient, LLMServiceError, ModelUsage
from backend.app.services.rag import NO_RELEVANT_KNOWLEDGE, RAGService
from backend.app.services.request_trace import TraceRecorder, get_request_trace_store
from backend.app.services.reranker import RerankerUnavailableError
from backend.tests.test_agent_tools import FakeCatalog
from backend.tests.test_llm import FakeStream, make_client, tool_response
from backend.tests.test_rag import StubLLMClient, StubRetrievalService, retrieved_chunk


@contextmanager
def client_for(service: RAGService) -> Iterator[TestClient]:
    app.dependency_overrides[require_rag_service] = lambda: service
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def make_service(results: list[Any], llm: StubLLMClient | LLMClient | None = None) -> tuple[RAGService, StubRetrievalService]:
    retrieval = StubRetrievalService(results)
    service = RAGService(retrieval, llm or StubLLMClient(), RAGSettings(_env_file=None))
    return service, retrieval


def test_recorder_persists_one_row_with_actual_usage_and_unknown_totals() -> None:
    store = get_request_trace_store()
    first = TraceRecorder("question A", mode="json", model="test-model")
    rewrite = first.begin_model_call("rewrite")
    selection = first.begin_model_call("tool_selection")
    first.record_model_usage(rewrite, ModelUsage(12, 4))
    first.record_model_usage(selection, ModelUsage(8, 2))
    first.mark_committed()
    first.finish(store, outcome="success", http_status=200)
    first.finish(store, outcome="error", http_status=500)

    second = TraceRecorder("question B", mode="sse")
    stage = second.begin_model_call("generation")
    second.record_model_usage(stage, ModelUsage(10, None))
    second.finish(store, outcome="cancelled", http_status=200, error_code="client_disconnected")

    rows = {row.id: row for row in store.recent(100)}
    assert len(rows) == 2
    assert (rows[first.id].prompt_tokens, rows[first.id].completion_tokens) == (20, 6)
    assert rows[first.id].usage_complete and rows[first.id].business_committed
    assert rows[first.id].outcome == "success"
    assert rows[second.id].prompt_tokens is None and rows[second.id].completion_tokens is None
    assert not rows[second.id].usage_complete and not rows[second.id].business_committed
    assert rows[second.id].outcome == "cancelled"
    assert rows[second.id].latency_ms >= 0


def test_request_log_rejects_invalid_mode_or_outcome() -> None:
    store = get_request_trace_store()
    trace = TraceRecorder("question", mode="json")
    trace.finish(store, outcome="success", http_status=200)
    row = store.recent(1)[0]
    values = {column.name: getattr(row, column.name) for column in RequestLog.__table__.columns}
    for column, invalid in (("mode", "raw"), ("outcome", "unknown")):
        bad = {**values, "id": uuid4(), column: invalid}
        with pytest.raises(IntegrityError):
            store.save(bad)
    assert [item.id for item in store.recent(10)] == [trace.id]


def test_real_llm_client_usage_is_aggregated_through_the_graph_without_network() -> None:
    llm, sdk = make_client()

    def create(**options: Any) -> Any:
        if options.get("tool_choice") == "required":
            response = tool_response("search_knowledge_base", '{"query":"question"}')
            response.usage = SimpleNamespace(prompt_tokens=10, completion_tokens=2)
            return response
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="answer"))],
            usage=SimpleNamespace(prompt_tokens=20, completion_tokens=5),
        )

    sdk.completions.create = create
    service, _ = make_service([retrieved_chunk(score=0.9)], llm)
    with client_for(service) as client:
        response = client.post("/chat", json={"message": "question"})
    row = get_request_trace_store().recent(1)[0]
    assert response.status_code == 200 and row.answer == response.json()["answer"]
    assert row.usage_complete and (row.prompt_tokens, row.completion_tokens) == (30, 7)
    assert row.model_calls == [
        {"stage": "tool_selection", "prompt_tokens": 10, "completion_tokens": 2},
        {"stage": "generation", "prompt_tokens": 20, "completion_tokens": 5},
    ]


@pytest.mark.parametrize("usage_has_choice", [False, True], ids=["empty_choices", "deepseek_choice"])
def test_stream_usage_in_final_chunk_is_aggregated_through_the_graph(
    usage_has_choice: bool,
) -> None:
    llm, sdk = make_client()
    options_seen: list[dict[str, Any]] = []

    def create(**options: Any) -> Any:
        options_seen.append(options)
        if options.get("tool_choice") == "required":
            response = tool_response("search_knowledge_base", '{"query":"question"}')
            response.usage = SimpleNamespace(prompt_tokens=11, completion_tokens=2)
            return response
        return FakeStream([
            SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="answer"))], usage=None),
            SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content=""), finish_reason="stop")]
                if usage_has_choice else [],
                usage=SimpleNamespace(prompt_tokens=19, completion_tokens=4),
            ),
        ])

    sdk.completions.create = create
    service, _ = make_service([retrieved_chunk(score=0.9)], llm)
    with client_for(service) as client:
        response = client.post("/chat", json={"message": "question", "stream": True})
    row = get_request_trace_store().recent(1)[0]
    assert response.status_code == 200 and "data: [DONE]" in response.text
    assert row.answer == "answer" and row.business_committed
    assert row.usage_complete and (row.prompt_tokens, row.completion_tokens) == (30, 6)
    assert any(options.get("stream_options") == {"include_usage": True} for options in options_seen)


@pytest.mark.parametrize("stream", [False, True])
def test_chat_trace_records_same_search_candidates_gate_and_public_sources(stream: bool) -> None:
    high = retrieved_chunk(score=0.85, filename="policy.pdf", page=1, content="private-high")
    duplicate = retrieved_chunk(score=0.7, filename="policy.pdf", page=1, content="private-duplicate")
    low = replace(retrieved_chunk(score=0.2, filename="other.pdf", page=9,
                                  content="private-low"), vector_score=0.2)
    service, retrieval = make_service([high, duplicate, low])
    with client_for(service) as client:
        response = client.post("/chat", json={"message": "  规则？  ", "stream": stream})

    assert response.status_code == 200
    assert retrieval.questions == ["规则？"]
    row = get_request_trace_store().recent(10)[0]
    assert row.query == row.standalone_query == "规则？"
    assert row.mode == ("sse" if stream else "json")
    assert row.business_committed and row.outcome == "success" and row.http_status == 200
    assert [item["chunk_id"] for item in row.retrieved_docs] == [str(high.chunk_id), str(duplicate.chunk_id), str(low.chunk_id)]
    assert [item["included_in_context"] for item in row.retrieved_docs] == [True, True, False]
    assert [item["vector_score"] for item in row.retrieved_docs] == [0.85, 0.7, 0.2]
    assert row.sources == [{"filename": "policy.pdf", "page": 1}]
    assert row.tool_calls == [{"name": "search_knowledge_base", "call_id": "test-call", "status": "success"}]
    assert [call["stage"] for call in row.model_calls] == ["tool_selection", "generation"]
    assert not row.usage_complete and row.prompt_tokens is None
    assert "private-high" not in json.dumps(row.retrieved_docs)
    if stream:
        assert 'event: sources\ndata: {"sources": [{"filename": "policy.pdf", "page": 1}]}' in response.text
        assert "data: [DONE]" in response.text
        assert row.answer == "answer"
    else:
        assert response.json()["sources"] == row.sources
        assert row.answer == response.json()["answer"]


@pytest.mark.parametrize("kind", ["refusal", "catalog"])
def test_refusal_and_catalog_traces_have_no_search_candidates(kind: str) -> None:
    if kind == "refusal":
        llm = StubLLMClient()
        service, retrieval = make_service([retrieved_chunk(score=0.2)], llm)
    else:
        llm = StubLLMClient(tool_call=AgentToolCall(call_id="catalog-call", name="list_documents", arguments={}))
        service, retrieval = make_service([], llm)
        service._catalog_factory = lambda: FakeCatalog()
    with client_for(service) as client:
        response = client.post("/chat", json={"message": "有哪些文档？" if kind == "catalog" else "无关问题"})
    row = get_request_trace_store().recent(1)[0]
    assert response.status_code == 200 and row.outcome == "success"
    assert row.sources == []
    assert [call["stage"] for call in row.model_calls] == (["tool_selection"] if kind == "refusal" else ["tool_selection", "generation"])
    if kind == "refusal":
        assert row.answer == NO_RELEVANT_KNOWLEDGE and retrieval.questions == ["无关问题"]
        assert len(row.retrieved_docs) == 1 and not row.retrieved_docs[0]["included_in_context"]
    else:
        assert row.tool_calls[0]["name"] == "list_documents" and retrieval.questions == []
        assert row.retrieved_docs == []


def test_followup_trace_records_rewrite_stage_and_independent_search_query() -> None:
    service, retrieval = make_service([retrieved_chunk(score=0.9)])
    llm = service._llm_client
    with client_for(service) as client:
        first = client.post("/chat", json={"message": "原问题"})
        assert first.status_code == 200
        llm.rewritten_query = "独立问题"
        second = client.post("/chat", json={"message": "它呢？", "session_id": first.json()["session_id"]})
    assert second.status_code == 200
    rows = get_request_trace_store().recent(10)
    followup = next(row for row in rows if row.query == "它呢？")
    assert followup.standalone_query == "独立问题"
    assert [call["stage"] for call in followup.model_calls] == ["rewrite", "tool_selection", "generation"]
    assert retrieval.questions == ["原问题", "独立问题"]
    assert followup.session_id == UUID(first.json()["session_id"])


def test_http_and_sse_failures_are_distinct_from_successful_delivery() -> None:
    class BrokenLLM(StubLLMClient):
        def complete_messages(self, messages: Any) -> str:
            raise LLMServiceError("private-provider-error")

        def stream_messages(self, messages: Any) -> Iterator[str]:
            yield "partial"
            raise LLMServiceError("private-provider-error")

    service, _ = make_service([retrieved_chunk(score=0.9)], BrokenLLM())
    with client_for(service) as client:
        json_response = client.post("/chat", json={"message": "json-failure"})
        sse_response = client.post("/chat", json={"message": "sse-failure", "stream": True})
        missing = client.post("/chat", json={"message": "missing-session", "session_id": str(uuid4())})
    assert json_response.status_code == 502
    assert sse_response.status_code == 200 and "event: error" in sse_response.text
    assert "[DONE]" not in sse_response.text
    assert missing.status_code == 404
    rows = {row.query: row for row in get_request_trace_store().recent(10)}
    assert len(rows) == 3
    assert (rows["json-failure"].outcome, rows["json-failure"].http_status) == ("error", 502)
    assert (rows["sse-failure"].outcome, rows["sse-failure"].http_status) == ("error", 200)
    assert rows["sse-failure"].error_code == "llm_stream_failed"
    assert rows["missing-session"].error_code == "ConversationNotFoundError"
    assert all(not row.business_committed for row in rows.values())


def test_sse_prefetch_retrieval_failure_records_selected_tool_error(monkeypatch: pytest.MonkeyPatch) -> None:
    service, retrieval = make_service([])

    def fail_search(question: str) -> Any:
        raise RerankerUnavailableError("private model path")

    monkeypatch.setattr(retrieval, "search", fail_search)
    with client_for(service) as client:
        response = client.post("/chat", json={"message": "question", "stream": True})
    row = get_request_trace_store().recent(1)[0]
    assert response.status_code == 503 and "private model path" not in response.text
    assert row.mode == "sse" and row.outcome == "error" and row.http_status == 503
    assert row.tool_calls[0]["status"] == "error"
    assert row.retrieved_docs == [] and not row.business_committed


@pytest.mark.parametrize("stream", [False, True])
def test_conversation_save_failure_has_no_committed_trace(
    monkeypatch: pytest.MonkeyPatch, stream: bool,
) -> None:
    service, _ = make_service([retrieved_chunk(score=0.9)])

    def fail_save(**kwargs: Any) -> None:
        raise ConversationMemoryError("private database detail")

    monkeypatch.setattr(service._memory, "append_turn", fail_save)
    with client_for(service) as client:
        response = client.post("/chat", json={"message": "question", "stream": stream})
    row = get_request_trace_store().recent(1)[0]
    assert row.outcome == "error" and not row.business_committed and row.answer is None
    if stream:
        assert row.http_status == 200 and row.error_code == "conversation_save_failed"
        assert "event: error" in response.text and "[DONE]" not in response.text
    else:
        assert row.http_status == 500 and row.error_code == "ConversationMemoryError"
        assert response.status_code == 500
    assert "private database detail" not in response.text


@pytest.mark.parametrize("send_failure_on", [b'"delta"', b"event: sources"])
def test_client_disconnect_records_commit_boundary(send_failure_on: bytes) -> None:
    service, _ = make_service([retrieved_chunk(score=0.9)])
    response = chat(ChatRequest(message="question", stream=True), service)
    assert response.status_code == 200

    async def invoke() -> None:
        async def receive() -> dict[str, str]:
            await anyio.sleep_forever()
            return {"type": "http.disconnect"}

        async def send(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.body" and send_failure_on in message.get("body", b""):
                raise OSError("client went away")

        with pytest.raises(Exception):
            await response({"type": "http", "method": "POST", "path": "/chat",
                            "asgi": {"version": "3.0", "spec_version": "2.4"}, "headers": []}, receive, send)

    anyio.run(invoke, backend="asyncio")
    row = get_request_trace_store().recent(1)[0]
    assert row.outcome == "cancelled" and row.error_code == "client_disconnected"
    assert row.business_committed is (send_failure_on == b"event: sources")
    assert row.answer == ("answer" if row.business_committed else None)


def test_trace_store_failure_keeps_chat_response_and_logs_only_error_class(monkeypatch: pytest.MonkeyPatch) -> None:
    class BrokenStore:
        def save(self, values: dict[str, object]) -> None:
            raise RuntimeError("private-query-and-answer")

    monkeypatch.setattr("backend.app.api.chat.get_request_trace_store", lambda: BrokenStore())
    service, _ = make_service([retrieved_chunk(score=0.9)])
    logs: list[str] = []
    handler = logger.add(lambda message: logs.append(str(message)))
    try:
        with client_for(service) as client:
            response = client.post("/chat", json={"message": "private-question"})
    finally:
        logger.remove(handler)
    assert response.status_code == 200
    assert "private-query-and-answer" not in "".join(logs)
    assert "private-question" not in "".join(logs)
    assert "Chat trace persistence failed: RuntimeError" in "".join(logs)
