"""Inject one tool selector, one executor, and the existing generation lifecycle."""

from collections.abc import Callable
from threading import Event
from typing import Protocol

from langgraph.config import get_stream_writer
from langgraph.runtime import RunControl, Runtime

from backend.app.agent.state import AgentContext, AgentState, AgentUpdate
from backend.app.agent.tools import AgentTools, TOOL_SELECTION_PROMPT, tool_definitions
from backend.app.core.config import RAGSettings
from backend.app.services.llm import LLMClient, LLMServiceError, validate_tool_call
from backend.app.services.rag import (
    NO_RELEVANT_KNOWLEDGE,
    PreparedRAG,
    RAGGraphError,
    _sanitized_model_deltas,
    _strip_model_source_references,
)
from backend.app.services.reranker import RerankedRetrievalService


class AgentNode(Protocol):
    """The node boundary: read state and return a partial update."""

    def __call__(
        self, state: AgentState, runtime: Runtime[AgentContext]
    ) -> AgentUpdate: ...


class StreamControl(RunControl):
    """Per-run cancellation and one-delta backpressure, never part of State."""

    def __init__(self) -> None:
        super().__init__()
        self._resume = Event()

    def acknowledge(self) -> None:
        """Allow the producer to request the next upstream delta."""
        self._resume.set()

    def cancel(self) -> None:
        """Wake a paused producer so its finally block closes the upstream."""
        self.request_drain("client_closed")
        self._resume.set()

    def emit(
        self, writer: Callable[[object], None], delta: str
    ) -> bool:
        """Publish one custom delta and wait for the consumer or cancellation."""
        self._resume.clear()
        if self.drain_requested:
            return False
        writer({"type": "delta", "delta": delta})
        self._resume.wait()
        return not self.drain_requested


def create_retrieve_node(
    retrieval_service: RerankedRetrievalService,
    settings: RAGSettings,
) -> AgentNode:
    """Retain the internal prepare adapter using the same search-tool business code."""
    tools = AgentTools(retrieval_service, settings)

    def retrieve_node(
        state: AgentState, runtime: Runtime[AgentContext]
    ) -> AgentUpdate:
        from backend.app.agent.state import initial_agent_state

        question = initial_agent_state(state["query"])["query"]
        execution = tools.search_knowledge_base(question)
        return AgentUpdate(
            query=question, retrieved_docs=execution.retrieved_docs, prepared=execution.prepared,
            needs_tool_selection=False,
        )

    return retrieve_node


def create_select_tool_node(llm_client: LLMClient) -> AgentNode:
    """Select once; malformed model suggestions cannot reach an executor."""
    def select_tool_node(state: AgentState, runtime: Runtime[AgentContext]) -> AgentUpdate:
        if (state.get("needs_tool_selection") is not True or state.get("tool_calls") != ()
                or state.get("prepared") is not None):
            raise RAGGraphError("The RAG graph tool selection state is invalid.")
        call = validate_tool_call(llm_client.select_tool((
            {"role": "system", "content": TOOL_SELECTION_PROMPT},
            {"role": "user", "content": state["query"]},
        ), tool_definitions()))
        return AgentUpdate(tool_calls=(call,), needs_tool_selection=False)
    return select_tool_node


def create_tool_node(tools: AgentTools) -> AgentNode:
    """Execute exactly one locally validated read-only tool."""
    def tool_node(state: AgentState, runtime: Runtime[AgentContext]) -> AgentUpdate:
        calls = state.get("tool_calls")
        if (state.get("needs_tool_selection") is not False or not isinstance(calls, tuple)
                or len(calls) != 1 or state.get("prepared") is not None):
            raise RAGGraphError("The RAG graph tool execution state is invalid.")
        execution = tools.execute(calls[0], original_query=state["query"])
        return AgentUpdate(prepared=execution.prepared, retrieved_docs=execution.retrieved_docs)
    return tool_node


def create_generate_node(llm_client: LLMClient) -> AgentNode:
    """Reuse the existing Prompt, refusal and citation sanitizer."""

    def generate_node(
        state: AgentState, runtime: Runtime[AgentContext]
    ) -> AgentUpdate:
        prepared = state.get("prepared")
        calls = state.get("tool_calls")
        if (not isinstance(prepared, PreparedRAG) or state.get("needs_tool_selection") is not False
                or not isinstance(calls, tuple) or len(calls) not in {0, 1}):
            raise RAGGraphError("The RAG graph has no valid prepared context.")
        if calls:
            validate_tool_call(calls[0])
        preserve_filenames = bool(calls and calls[0]["name"] in {"list_documents", "get_document_detail"})
        context = runtime.context
        if context is None or context.get("response_mode") not in {"complete", "stream"}:
            raise RAGGraphError("The RAG graph response mode is invalid.")
        streaming = context["response_mode"] == "stream"
        if not prepared.has_relevant_context:
            if streaming:
                writer = get_stream_writer()
                control = runtime.control
                if isinstance(control, StreamControl):
                    control.emit(writer, NO_RELEVANT_KNOWLEDGE)
                else:
                    writer({"type": "delta", "delta": NO_RELEVANT_KNOWLEDGE})
            return AgentUpdate(answer=NO_RELEVANT_KNOWLEDGE)

        if not streaming:
            answer = _strip_model_source_references(
                llm_client.complete_messages(prepared.messages), preserve_filenames=preserve_filenames,
            )
            if not answer.strip():
                raise LLMServiceError("The language model returned an empty response")
            return AgentUpdate(answer=answer)

        writer = get_stream_writer()
        control = runtime.control
        parts: list[str] = []
        raw = llm_client.stream_messages(prepared.messages)
        sanitized = _sanitized_model_deltas(raw, preserve_filenames=preserve_filenames)
        try:
            for delta in sanitized:
                parts.append(delta)
                if isinstance(control, StreamControl):
                    if not control.emit(writer, delta):
                        return AgentUpdate(answer="".join(parts))
                else:
                    writer({"type": "delta", "delta": delta})
        finally:
            sanitized.close()
            close = getattr(raw, "close", None)
            if callable(close):
                close()
        answer = "".join(parts)
        if not answer.strip():
            raise LLMServiceError("The language model returned an empty stream")
        return AgentUpdate(answer=answer)

    return generate_node
