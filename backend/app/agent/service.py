"""Translate the compiled graph into the unchanged RAG answer/delta contract."""

from collections.abc import Callable, Iterator
from contextvars import Context, copy_context
from dataclasses import dataclass, field
from threading import RLock
from typing import Any
from uuid import UUID

from langsmith import tracing_context

from backend.app.agent.graph import CompiledRAGGraph
from backend.app.agent.nodes import StreamControl
from backend.app.agent.state import AgentState, initial_agent_state
from backend.app.services.bm25 import BM25Error
from backend.app.services.embedding import EmbeddingError
from backend.app.services.hybrid import HybridError
from backend.app.services.llm import LLMServiceError
from backend.app.services.llm import LLMToolCallError, validate_tool_call
from backend.app.services.document_catalog import DocumentCatalogError
from backend.app.services.qdrant_store import QdrantStoreError
from backend.app.services.rag import PreparedRAG, RAGAnswer, RAGGraphError
from backend.app.services.reranker import RerankerError
from backend.app.services.conversation_memory import ConversationHistoryMessage, ConversationMemoryError

_KNOWN_FAILURES = (
    BM25Error, EmbeddingError, HybridError, QdrantStoreError, RerankerError,
    LLMServiceError, RAGGraphError, DocumentCatalogError, ConversationMemoryError,
)


@dataclass(slots=True)
class PreparedRAGStream:
    """One iterator and its safe sources; no persistence or exposed graph State."""

    events: Iterator[Any]
    prepared: PreparedRAG | None = None
    control: StreamControl = field(default_factory=StreamControl)
    closed: bool = False
    session_id: UUID | None = None
    answer: str = ""
    on_success: Callable[[str], None] | None = field(default=None, repr=False)
    on_failure: Callable[[], None] | None = field(default=None, repr=False)
    on_close: Callable[[], None] | None = field(default=None, repr=False)
    _context: Context = field(default_factory=copy_context, repr=False)
    _lock: RLock = field(default_factory=RLock, repr=False)

    def next_event(self) -> Any:
        """Keep the generator in one Context across FastAPI worker threads."""
        with self._lock:
            if self.closed:
                raise StopIteration
            return self._context.run(next, self.events)

    def cancel(self) -> None:
        """Signal before waiting on an in-flight graph iterator."""
        self.control.cancel()

    def finish(self) -> None:
        """Keep ownership through persistence; cancel can signal while close waits."""
        with self._lock:
            if self.closed or self.control.drain_requested:
                raise RAGGraphError("The RAG graph stream was cancelled.")
            if self.on_success is not None:
                self.on_success(self.answer)

    def fail(self) -> None:
        """Run request-failure compensation before releasing stream ownership."""
        with self._lock:
            if self.on_failure is not None:
                callback, self.on_failure = self.on_failure, None
                callback()

    def close(self) -> None:
        """Idempotently stop the producer and close the same graph iterator."""
        self.cancel()
        with self._lock:
            if self.closed:
                return
            self.closed = True
            close = getattr(self.events, "close", None)
            try:
                if callable(close):
                    self._context.run(close)
            except Exception as exc:
                raise RAGGraphError("The RAG graph stream could not be closed.") from exc
            finally:
                if self.on_close is not None:
                    self.on_close()


def _initial_state(
    question: str | PreparedRAG, history: tuple[ConversationHistoryMessage, ...] = (),
) -> AgentState:
    if isinstance(question, PreparedRAG):
        state = initial_agent_state(question.question)
        state.update(prepared=question, needs_tool_selection=False)
        return state
    return initial_agent_state(question, history=history)


def _event_data(event: Any) -> tuple[str, dict[str, Any]]:
    if (
        not isinstance(event, dict) or event.get("ns") != ()
        or event.get("type") not in {"updates", "custom"}
        or not isinstance(event.get("data"), dict)
    ):
        raise RAGGraphError("The RAG graph returned an invalid stream event.")
    return event["type"], event["data"]


class RAGGraphRunner:
    """Own graph invocation and prefetch; HTTP never receives internal updates."""

    def __init__(self, graph: CompiledRAGGraph, model: str) -> None:
        self.graph = graph
        self.model = model

    def complete(
        self, question: str | PreparedRAG, *, history: tuple[ConversationHistoryMessage, ...] = (),
    ) -> RAGAnswer:
        """Run the complete graph once, preserving all known service exceptions."""
        initial = _initial_state(question, history)
        try:
            with tracing_context(enabled=False):
                state = self.graph.invoke(
                    initial, context={"response_mode": "complete"},
                    config={"callbacks": []},
                )
            prepared = state.get("prepared")
            answer = state.get("answer")
            calls = state.get("tool_calls")
            expected_calls = 1 if initial["needs_tool_selection"] else 0
            if (
                not isinstance(prepared, PreparedRAG)
                or not isinstance(answer, str) or not answer.strip()
                or not isinstance(calls, tuple) or len(calls) != expected_calls
                or state.get("needs_tool_selection") is not False
                or state.get("query") != initial["query"] or prepared.question != initial["query"]
                or state.get("needs_query_rewrite") is not False
                or state.get("history") != initial["history"]
                or not isinstance(state.get("standalone_query"), str)
                or not 1 <= len(state["standalone_query"]) <= 4096
                or (not initial["needs_query_rewrite"]
                    and state["standalone_query"] != initial["standalone_query"])
            ):
                raise RAGGraphError("The RAG graph returned an invalid final state.")
            if calls:
                try:
                    validate_tool_call(calls[0])
                except LLMToolCallError as exc:
                    raise RAGGraphError("The RAG graph returned an invalid final state.") from exc
            return RAGAnswer(answer, self.model, prepared.sources)
        except _KNOWN_FAILURES:
            raise
        except MemoryError:
            raise
        except Exception as exc:
            raise RAGGraphError("The RAG graph failed.") from exc

    def _events(
        self, initial: AgentState, control: StreamControl
    ) -> Iterator[Any]:
        try:
            with tracing_context(enabled=False):
                yield from self.graph.stream(
                    initial, context={"response_mode": "stream"},
                    config={"callbacks": []}, control=control,
                    stream_mode=["updates", "custom"], version="v2",
                )
        except _KNOWN_FAILURES:
            raise
        except MemoryError:
            raise
        except Exception as exc:
            raise RAGGraphError("The RAG graph stream failed.") from exc

    def start_stream(
        self, question: str | PreparedRAG, *, history: tuple[ConversationHistoryMessage, ...] = (),
    ) -> PreparedRAGStream:
        """Prefetch selection and execution, before generation or StreamingResponse."""
        initial = _initial_state(question, history)
        control = StreamControl()
        run = PreparedRAGStream(
            self._events(initial, control),
            prepared=initial["prepared"], control=control,
        )
        if not initial["needs_tool_selection"]:
            return run
        try:
            if initial["needs_query_rewrite"]:
                kind, data = _event_data(run.next_event())
                rewritten = data.get("rewrite_query_node")
                if (kind != "updates" or set(data) != {"rewrite_query_node"}
                        or not isinstance(rewritten, dict)
                        or set(rewritten) != {"standalone_query", "needs_query_rewrite"}
                        or rewritten.get("needs_query_rewrite") is not False
                        or not isinstance(rewritten.get("standalone_query"), str)
                        or not 1 <= len(rewritten["standalone_query"].strip()) <= 4096):
                    raise RAGGraphError("The RAG graph did not finish query rewriting.")
            event = run.next_event()
            kind, data = _event_data(event)
            selection = data.get("select_tool_node")
            if (
                kind != "updates" or set(data) != {"select_tool_node"}
                or not isinstance(selection, dict)
                or set(selection) != {"tool_calls", "needs_tool_selection"}
                or selection.get("needs_tool_selection") is not False
                or not isinstance(selection.get("tool_calls"), tuple)
                or len(selection["tool_calls"]) != 1
            ):
                raise RAGGraphError("The RAG graph did not finish tool selection.")
            try:
                validate_tool_call(selection["tool_calls"][0])
            except LLMToolCallError as exc:
                raise RAGGraphError("The RAG graph returned an invalid tool selection.") from exc
            kind, data = _event_data(run.next_event())
            update = data.get("tool_node")
            if (kind != "updates" or set(data) != {"tool_node"} or not isinstance(update, dict)
                    or set(update) != {"prepared", "retrieved_docs"}
                    or not isinstance(update.get("retrieved_docs"), tuple)):
                raise RAGGraphError("The RAG graph did not finish tool execution.")
            prepared = update.get("prepared")
            if not isinstance(prepared, PreparedRAG) or prepared.question != initial["query"]:
                raise RAGGraphError("The RAG graph returned no prepared context.")
            run.prepared = prepared
            return run
        except StopIteration as exc:
            run.close()
            raise RAGGraphError("The RAG graph did not finish tool execution.") from exc
        except BaseException:
            run.close()
            raise

    def stream(self, run: PreparedRAGStream) -> Iterator[str]:
        """Expose sanitized custom deltas only, requiring a final generate update."""
        finished = False
        parts: list[str] = []
        try:
            while True:
                try:
                    event = run.next_event()
                except StopIteration:
                    break
                kind, data = _event_data(event)
                if kind == "custom":
                    if (
                        finished or set(data) != {"type", "delta"}
                        or data.get("type") != "delta"
                        or not isinstance(data.get("delta"), str) or not data["delta"]
                    ):
                        raise RAGGraphError("The RAG graph returned an invalid delta.")
                    parts.append(data["delta"])
                    yield data["delta"]
                    run.control.acknowledge()
                else:
                    update = data.get("generate_node")
                    if (
                        finished or set(data) != {"generate_node"}
                        or not isinstance(update, dict)
                        or not isinstance(update.get("answer"), str)
                        or not update["answer"].strip()
                    ):
                        raise RAGGraphError("The RAG graph returned an invalid generation update.")
                    finished = True
                    run.answer = update["answer"]
            if not finished or run.prepared is None:
                raise RAGGraphError("The RAG graph did not finish generation.")
            if run.answer != "".join(parts) or run.control.drain_requested:
                raise RAGGraphError("The RAG graph stream did not complete successfully.")
            run.finish()
        except Exception:
            run.fail()
            raise
        finally:
            run.close()
