"""Day14 graph input/state boundaries without services or credentials."""

from typing import get_type_hints

import pytest

from backend.app.agent.state import AgentContext, AgentState, initial_agent_state


def test_state_contains_only_request_data_and_context_only_mode() -> None:
    assert set(get_type_hints(AgentState)) == {
        "query", "retrieved_docs", "prepared", "answer", "tool_calls", "needs_retrieval"
    }
    assert set(get_type_hints(AgentContext)) == {"response_mode"}
    state = initial_agent_state("  报销时间？  ")
    assert state == {
        "query": "报销时间？", "retrieved_docs": (), "prepared": None,
        "answer": "", "tool_calls": (), "needs_retrieval": True,
    }
    other = initial_agent_state("another")
    state["answer"] = "changed"
    assert other["answer"] == ""


@pytest.mark.parametrize(
    "query", ["", "   ", "q" * 4097, None, True, 4],
    ids=["empty", "blank", "overlong", "none", "bool", "number"],
)
def test_invalid_direct_input_is_rejected(query: object) -> None:
    with pytest.raises(ValueError):
        initial_agent_state(query)  # type: ignore[arg-type]
