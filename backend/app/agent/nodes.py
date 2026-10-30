"""Inject existing retrieval and generation services into two graph nodes."""

from collections.abc import Callable
from threading import Event
from typing import Protocol

from langgraph.config import get_stream_writer
from langgraph.runtime import RunControl, Runtime

from backend.app.agent.state import AgentContext, AgentState, AgentUpdate
from backend.app.core.config import RAGSettings
from backend.app.services.llm import LLMClient, LLMServiceError
from backend.app.services.rag import (
    NO_RELEVANT_KNOWLEDGE,
    PreparedRAG,
    RAGGraphError,
    _sanitized_model_deltas,
    _strip_model_source_references,
    build_rag_messages,
    build_sources,
    select_relevant_chunks,
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
    """Keep Top5 intact while using the existing vector gate for actual Context."""

    def retrieve_node(
        state: AgentState, runtime: Runtime[AgentContext]
    ) -> AgentUpdate:
        from backend.app.agent.state import initial_agent_state

        question = initial_agent_state(state["query"])["query"]
        retrieved = tuple(retrieval_service.search(question).results)
        relevant = select_relevant_chunks(
            retrieved, min_score=settings.min_relevance_score
        )
        prepared = PreparedRAG(
            question=question,
            messages=build_rag_messages(question, relevant) if relevant else (),
            sources=build_sources(relevant),
            has_relevant_context=bool(relevant),
        )
        return AgentUpdate(
            query=question, retrieved_docs=retrieved, prepared=prepared,
            needs_retrieval=False,
        )

    return retrieve_node


def create_generate_node(llm_client: LLMClient) -> AgentNode:
    """Reuse the existing Prompt, refusal and citation sanitizer."""

    def generate_node(
        state: AgentState, runtime: Runtime[AgentContext]
    ) -> AgentUpdate:
        prepared = state.get("prepared")
        if not isinstance(prepared, PreparedRAG) or state.get("tool_calls") != ():
            raise RAGGraphError("The RAG graph has no valid prepared context.")
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
                llm_client.complete_messages(prepared.messages)
            )
            if not answer.strip():
                raise LLMServiceError("The language model returned an empty response")
            return AgentUpdate(answer=answer)

        writer = get_stream_writer()
        control = runtime.control
        parts: list[str] = []
        raw = llm_client.stream_messages(prepared.messages)
        sanitized = _sanitized_model_deltas(raw)
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
