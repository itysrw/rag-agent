"""Graph streaming prefetch, live deltas, safe errors, and cleanup."""

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest

from backend.app.agent.service import RAGGraphRunner
from backend.app.core.config import RAGSettings
from backend.app.services.llm import LLMServiceError
from backend.app.services.rag import RAGGraphError, RAGService
from backend.app.services.reranker import RerankerInputError
from backend.tests.test_rag import StubLLMClient, StubRetrievalService, retrieved_chunk


class TrackingLLM(StubLLMClient):
    def __init__(self) -> None:
        super().__init__()
        self.produced: list[str] = []
        self.closed = 0

    def stream_messages(self, messages: Any) -> Iterator[str]:
        self.stream_calls.append(messages)
        try:
            for value in ("first", "second", "third"):
                self.produced.append(value)
                yield value
        finally:
            self.closed += 1


def test_prefetch_is_retrieval_only_then_deltas_are_live_and_close_upstream() -> None:
    llm = TrackingLLM()
    retrieval = StubRetrievalService([retrieved_chunk(score=0.9)])
    service = RAGService(retrieval, llm, RAGSettings(_env_file=None))
    run = service.start_stream("question")
    assert retrieval.questions == ["question"]
    assert llm.stream_calls == [] and llm.produced == []
    stream = service.stream(run)
    assert next(stream) == "first"
    assert llm.produced == ["first"], "Do not consume the complete upstream before delivery."
    stream.close()
    assert run.closed and llm.closed == 1
    assert llm.produced == ["first"]
    run.close()
    assert retrieval.questions == ["question"]


def test_iterator_can_resume_and_close_on_different_http_worker_threads() -> None:
    llm = TrackingLLM()
    service = RAGService(
        StubRetrievalService([retrieved_chunk(score=0.9)]), llm, RAGSettings(_env_file=None)
    )
    run = service.start_stream("question")
    deltas = service.stream(run)
    with ThreadPoolExecutor(max_workers=1) as pool:
        assert pool.submit(next, deltas).result(timeout=5) == "first"
    deltas.close()
    assert llm.closed == 1 and run.closed


def test_close_after_prefetch_does_not_start_llm() -> None:
    llm = TrackingLLM()
    service = RAGService(
        StubRetrievalService([retrieved_chunk(score=0.9)]), llm, RAGSettings(_env_file=None)
    )
    run = service.start_stream("question")
    run.close()
    assert llm.stream_calls == []


def test_retrieval_error_propagates_before_any_streaming_or_llm() -> None:
    class Broken:
        def search(self, query: str) -> Any:
            raise RerankerInputError("private-query")
    llm = TrackingLLM()
    service = RAGService(Broken(), llm, RAGSettings(_env_file=None))
    with pytest.raises(RerankerInputError):
        service.start_stream("question")
    assert llm.stream_calls == []


@pytest.mark.parametrize("event", [
    None, {"type": "values", "ns": (), "data": {"private": "secret"}},
    {"type": "custom", "ns": (), "data": {"type": "delta", "delta": "secret"}},
    {"type": "updates", "ns": (), "data": {"retrieve_node": {}}},
])
def test_invalid_prefetch_events_fail_safely(event: Any) -> None:
    class BadGraph:
        def stream(self, *args: Any, **kwargs: Any) -> Iterator[Any]:
            yield event
    runner = RAGGraphRunner(BadGraph(), "test-model")
    with pytest.raises(RAGGraphError) as error:
        runner.start_stream("question")
    assert "secret" not in str(error.value)


def test_missing_generation_update_fails_instead_of_reporting_success() -> None:
    from backend.tests.test_chat import relevant_prepared
    prepared = relevant_prepared("question")
    class BadGraph:
        def stream(self, *args: Any, **kwargs: Any) -> Iterator[Any]:
            yield {"type": "updates", "ns": (), "data": {"retrieve_node": {"prepared": prepared}}}
            yield {"type": "custom", "ns": (), "data": {"type": "delta", "delta": "hello"}}
    runner = RAGGraphRunner(BadGraph(), "test-model")
    run = runner.start_stream("question")
    deltas = runner.stream(run)
    assert next(deltas) == "hello"
    with pytest.raises(RAGGraphError):
        next(deltas)
    assert run.closed


def test_forced_environment_tracing_cannot_export_state(monkeypatch: pytest.MonkeyPatch) -> None:
    import socket
    attempts: list[str] = []
    def forbidden(*args: Any, **kwargs: Any) -> None:
        attempts.append("network")
        raise AssertionError("No tracing network requests are permitted.")
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    retrieval = StubRetrievalService([retrieved_chunk(score=0.9)])
    service = RAGService(retrieval, StubLLMClient(), RAGSettings(_env_file=None))
    assert service.complete("private-question").answer
    assert list(service.stream(service.start_stream("private-question")))
    assert attempts == []


@pytest.mark.parametrize("missing", ["prepared", "answer"])
def test_incomplete_final_state_is_safe_failure(missing: str) -> None:
    from backend.tests.test_chat import relevant_prepared
    state = {"prepared": relevant_prepared(), "answer": "answer", "tool_calls": ()}
    state.pop(missing)
    class BadGraph:
        def invoke(self, *args: Any, **kwargs: Any) -> Any:
            return state
    with pytest.raises(RAGGraphError, match="invalid final state"):
        RAGGraphRunner(BadGraph(), "test-model").complete("question")


@pytest.mark.parametrize("event", [
    {"type": "custom", "ns": (), "data": {"type": "delta", "delta": 3}},
    {"type": "custom", "ns": (), "data": {"type": "delta", "delta": "secret", "prompt": "secret"}},
    {"type": "values", "ns": (), "data": {"private": "secret"}},
])
def test_bad_event_after_prefetch_is_not_exposed(event: Any) -> None:
    from backend.tests.test_chat import relevant_prepared
    class BadGraph:
        def stream(self, *args: Any, **kwargs: Any) -> Iterator[Any]:
            yield {"type": "updates", "ns": (), "data": {"retrieve_node": {"prepared": relevant_prepared()}}}
            yield event
    runner = RAGGraphRunner(BadGraph(), "test-model")
    run = runner.start_stream("question")
    with pytest.raises(RAGGraphError) as error:
        list(runner.stream(run))
    assert run.closed and "secret" not in str(error.value)
