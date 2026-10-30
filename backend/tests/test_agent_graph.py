"""The actual compiled graph: conditional entry and no persistence/tools."""

import pytest

from backend.app.agent.graph import build_rag_graph, route_tool_selection
from backend.app.agent.state import initial_agent_state
from backend.app.core.config import RAGSettings
from backend.app.services.rag import RAGGraphError, RAGService
from backend.tests.test_rag import StubLLMClient, StubRetrievalService, retrieved_chunk


def test_compiled_graph_selects_and_executes_exactly_one_tool() -> None:
    retrieval = StubRetrievalService([retrieved_chunk(score=0.9)])
    llm = StubLLMClient()
    graph = build_rag_graph(retrieval, llm, RAGSettings(_env_file=None))
    assert graph.checkpointer is None
    drawing = graph.get_graph()
    assert set(drawing.nodes) == {"__start__", "select_tool_node", "tool_node", "generate_node", "__end__"}
    conditional = {(e.source, e.target) for e in drawing.edges if e.conditional}
    assert conditional == {("__start__", "select_tool_node"), ("__start__", "generate_node")}
    assert {(e.source, e.target) for e in drawing.edges if not e.conditional} == {
        ("select_tool_node", "tool_node"), ("tool_node", "generate_node"), ("generate_node", "__end__")
    }
    initial = initial_agent_state(" question ")
    result = graph.invoke(initial, context={"response_mode": "complete"})
    assert initial["prepared"] is None
    assert len(result["tool_calls"]) == 1
    assert result["tool_calls"][0]["name"] == "search_knowledge_base"
    assert result["answer"] == "应在二十五日前提交。"
    assert retrieval.questions == ["question"] and len(llm.complete_calls) == 1
    assert len(llm.selection_calls) == 1
    assert route_tool_selection(result) == "generate_node"


def test_prepared_false_branch_skips_retrieval_and_missing_context_fails() -> None:
    retrieval = StubRetrievalService([retrieved_chunk(score=0.9)])
    llm = StubLLMClient()
    service = RAGService(retrieval, llm, RAGSettings(_env_file=None))
    prepared = service.prepare("question")
    graph = build_rag_graph(retrieval, llm, RAGSettings(_env_file=None))
    state = initial_agent_state("question")
    state.update(prepared=prepared, needs_tool_selection=False)
    assert graph.invoke(state, context={"response_mode": "complete"})["answer"]
    assert retrieval.questions == ["question"]
    assert len(llm.complete_calls) == 1
    assert llm.selection_calls == []
    state["prepared"] = None
    with pytest.raises(RAGGraphError):
        graph.invoke(state, context={"response_mode": "complete"})
    assert len(llm.complete_calls) == 1


def test_graph_compiles_lazily_once_per_service(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.agent import graph as module
    original = module.build_rag_graph
    builds: list[bool] = []
    def build(*args: object, **kwargs: object) -> object:
        builds.append(True)
        return original(*args, **kwargs)
    monkeypatch.setattr(module, "build_rag_graph", build)
    retrieval = StubRetrievalService([])
    service = RAGService(retrieval, StubLLMClient(), RAGSettings(_env_file=None))
    assert builds == [] and retrieval.questions == []
    service.complete("one")
    service.complete("two")
    run = service.start_stream("three")
    assert list(service.stream(run))
    assert builds == [True]
