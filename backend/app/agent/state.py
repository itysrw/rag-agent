"""Business state and immutable-per-run mode; service objects stay outside state."""

from collections.abc import Mapping
from typing import Literal

from typing_extensions import TypedDict

from backend.app.services.rag import PreparedRAG
from backend.app.services.reranker import RerankedChunk


class AgentState(TypedDict):
    """One request's values; serial nodes replace fields without reducers."""

    query: str
    retrieved_docs: tuple[RerankedChunk, ...]
    prepared: PreparedRAG | None
    answer: str
    tool_calls: tuple[Mapping[str, object], ...]
    needs_retrieval: bool


class AgentUpdate(TypedDict, total=False):
    """A node returns only the fields it writes."""

    query: str
    retrieved_docs: tuple[RerankedChunk, ...]
    prepared: PreparedRAG | None
    answer: str
    tool_calls: tuple[Mapping[str, object], ...]
    needs_retrieval: bool


class AgentContext(TypedDict):
    """Mode is runtime configuration, not persisted business state."""

    response_mode: Literal["complete", "stream"]


def initial_agent_state(query: str) -> AgentState:
    """Normalize a public request and always require knowledge-base retrieval."""
    if not isinstance(query, str) or not 1 <= len(query.strip()) <= 4096:
        raise ValueError("question must contain between 1 and 4096 characters")
    return AgentState(
        query=query.strip(), retrieved_docs=(), prepared=None, answer="",
        tool_calls=(), needs_retrieval=True,
    )
