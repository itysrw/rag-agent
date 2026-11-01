"""Business state and immutable-per-run mode; service objects stay outside state."""

from typing import Literal

from typing_extensions import TypedDict

from backend.app.services.rag import PreparedRAG
from backend.app.services.llm import AgentToolCall
from backend.app.services.reranker import RerankedChunk
from backend.app.services.conversation_memory import ConversationHistoryMessage, validate_history


class AgentState(TypedDict):
    """One request's values; serial nodes replace fields without reducers."""

    query: str
    standalone_query: str
    history: tuple[ConversationHistoryMessage, ...]
    needs_query_rewrite: bool
    retrieved_docs: tuple[RerankedChunk, ...]
    prepared: PreparedRAG | None
    answer: str
    tool_calls: tuple[AgentToolCall, ...]
    needs_tool_selection: bool


class AgentUpdate(TypedDict, total=False):
    """A node returns only the fields it writes."""

    standalone_query: str
    needs_query_rewrite: bool
    retrieved_docs: tuple[RerankedChunk, ...]
    prepared: PreparedRAG | None
    answer: str
    tool_calls: tuple[AgentToolCall, ...]
    needs_tool_selection: bool


class AgentContext(TypedDict):
    """Mode is runtime configuration, not persisted business state."""

    response_mode: Literal["complete", "stream"]


def initial_agent_state(
    query: str, *, history: tuple[ConversationHistoryMessage, ...] = (),
) -> AgentState:
    """Normalize a public request and require exactly one tool selection."""
    if not isinstance(query, str) or not 1 <= len(query.strip()) <= 4096:
        raise ValueError("question must contain between 1 and 4096 characters")
    if not isinstance(history, tuple) or len(history) > 10:
        raise ValueError("history must contain at most five complete turns")
    validate_history(history)
    return AgentState(
        query=query.strip(), retrieved_docs=(), prepared=None, answer="",
        tool_calls=(), needs_tool_selection=True,
        standalone_query=query.strip(), history=history, needs_query_rewrite=bool(history),
    )
