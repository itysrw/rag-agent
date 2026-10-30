"""Real node functions with the existing RAG gate and fake IO."""

from dataclasses import replace
from typing import Any

import pytest
from langgraph.runtime import Runtime

from backend.app.agent.nodes import create_generate_node, create_retrieve_node
from backend.app.agent.state import initial_agent_state
from backend.app.core.config import RAGSettings
from backend.app.services.llm import LLMServiceError
from backend.app.services.rag import NO_RELEVANT_KNOWLEDGE, RAGGraphError
from backend.tests.test_rag import StubLLMClient, StubRetrievalService, retrieved_chunk


def test_retrieve_preserves_top_five_but_prepares_only_vector_evidence() -> None:
    strong = replace(retrieved_chunk(score=0.8), score=-99.0)
    low = replace(retrieved_chunk(score=0.2, page=2), score=99.0)
    bm25_only = replace(retrieved_chunk(score=0.9, page=3), vector_score=None)
    retrieval = StubRetrievalService([strong, low, bm25_only])
    state = initial_agent_state("  question  ")
    before = dict(state)
    update = create_retrieve_node(retrieval, RAGSettings(_env_file=None))(
        state, Runtime(context={"response_mode": "complete"})
    )
    assert state == before
    assert retrieval.questions == ["question"]
    assert update["retrieved_docs"] == (strong, low, bm25_only)
    assert update["needs_retrieval"] is False
    prepared = update["prepared"]
    assert prepared is not None and prepared.has_relevant_context
    assert [(s.filename, s.page) for s in prepared.sources] == [(strong.filename, 1)]


@pytest.mark.parametrize("mode", ["complete", "stream"])
def test_empty_context_refuses_without_llm(
    mode: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    llm = StubLLMClient()
    state = initial_agent_state("question")
    state.update(create_retrieve_node(StubRetrievalService([]), RAGSettings(_env_file=None))(
        state, Runtime(context={"response_mode": "complete"})
    ))
    events: list[Any] = []
    monkeypatch.setattr("backend.app.agent.nodes.get_stream_writer", lambda: events.append)
    update = create_generate_node(llm)(state, Runtime(context={"response_mode": mode}))
    assert update["answer"] == NO_RELEVANT_KNOWLEDGE
    assert events == ([] if mode == "complete" else [{"type": "delta", "delta": NO_RELEVANT_KNOWLEDGE}])
    assert llm.complete_calls == llm.stream_calls == []


def test_generation_cleans_references_across_custom_deltas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    llm = StubLLMClient(stream_deltas=["Supported [fa", "ke.pdf page ", "99] [S", "99] answer"])
    state = initial_agent_state("question")
    state.update(create_retrieve_node(
        StubRetrievalService([retrieved_chunk(score=0.9)]), RAGSettings(_env_file=None)
    )(state, Runtime(context={"response_mode": "stream"})))
    before = dict(state)
    events: list[dict[str, str]] = []
    monkeypatch.setattr("backend.app.agent.nodes.get_stream_writer", lambda: events.append)
    update = create_generate_node(llm)(state, Runtime(context={"response_mode": "stream"}))
    assert state == before
    assert "".join(event["delta"] for event in events) == update["answer"] == "Supported   answer"
    assert all(set(event) == {"type", "delta"} for event in events)
    assert len(llm.stream_calls) == 1


def test_missing_prepared_state_never_calls_llm() -> None:
    llm = StubLLMClient()
    state = initial_agent_state("question")
    state["needs_retrieval"] = False
    with pytest.raises(RAGGraphError):
        create_generate_node(llm)(state, Runtime(context={"response_mode": "complete"}))
    assert llm.complete_calls == llm.stream_calls == []


@pytest.mark.parametrize("deltas", [[], [" ", "\t"], ["[fake.pdf page 99]"]])
def test_empty_or_only_reference_stream_remains_failure(
    deltas: list[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    llm = StubLLMClient(stream_deltas=deltas)
    state = initial_agent_state("question")
    state.update(create_retrieve_node(
        StubRetrievalService([retrieved_chunk(score=0.9)]), RAGSettings(_env_file=None)
    )(state, Runtime(context={"response_mode": "stream"})))
    monkeypatch.setattr("backend.app.agent.nodes.get_stream_writer", lambda: lambda _: None)
    with pytest.raises(LLMServiceError, match="empty stream"):
        create_generate_node(llm)(state, Runtime(context={"response_mode": "stream"}))


@pytest.mark.parametrize("answer", ["", "   ", "[fake.pdf page 99]"])
def test_empty_or_only_reference_complete_is_failure(answer: str) -> None:
    class EmptyLLM(StubLLMClient):
        def complete_messages(self, messages: Any) -> str:
            return answer
    state = initial_agent_state("question")
    state.update(create_retrieve_node(
        StubRetrievalService([retrieved_chunk(score=0.9)]), RAGSettings(_env_file=None)
    )(state, Runtime(context={"response_mode": "complete"})))
    with pytest.raises(LLMServiceError, match="empty response"):
        create_generate_node(EmptyLLM())(state, Runtime(context={"response_mode": "complete"}))
