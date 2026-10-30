"""Translate the compiled graph into the unchanged RAG answer/delta contract."""

from collections.abc import Iterator
from contextvars import Context, copy_context
from dataclasses import dataclass, field
from threading import RLock
from typing import Any

from langsmith import tracing_context

from backend.app.agent.graph import CompiledRAGGraph
from backend.app.agent.nodes import StreamControl
from backend.app.agent.state import AgentState, initial_agent_state
from backend.app.services.bm25 import BM25Error
from backend.app.services.embedding import EmbeddingError
from backend.app.services.hybrid import HybridError
from backend.app.services.llm import LLMServiceError
from backend.app.services.qdrant_store import QdrantStoreError
from backend.app.services.rag import PreparedRAG, RAGAnswer, RAGGraphError
from backend.app.services.reranker import RerankerError

_KNOWN_FAILURES = (
    BM25Error, EmbeddingError, HybridError, QdrantStoreError, RerankerError,
    LLMServiceError, RAGGraphError,
)


@dataclass(slots=True)
class PreparedRAGStream:
    """One iterator and its safe sources; no persistence or exposed graph State."""

    events: Iterator[Any]
    prepared: PreparedRAG | None = None
    control: StreamControl = field(default_factory=StreamControl)
    closed: bool = False
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

    def close(self) -> None:
        """Idempotently stop the producer and close the same graph iterator."""
        self.cancel()
        with self._lock:
            if self.closed:
                return
            self.closed = True
            close = getattr(self.events, "close", None)
            if callable(close):
                try:
                    self._context.run(close)
                except Exception as exc:
                    raise RAGGraphError("The RAG graph stream could not be closed.") from exc


def _initial_state(question: str | PreparedRAG) -> AgentState:
    if isinstance(question, PreparedRAG):
        state = initial_agent_state(question.question)
        state.update(prepared=question, needs_retrieval=False)
        return state
    return initial_agent_state(question)


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

    def complete(self, question: str | PreparedRAG) -> RAGAnswer:
        """Run the complete graph once, preserving all known service exceptions."""
        initial = _initial_state(question)
        try:
            with tracing_context(enabled=False):
                state = self.graph.invoke(
                    initial, context={"response_mode": "complete"},
                    config={"callbacks": []},
                )
            prepared = state.get("prepared")
            answer = state.get("answer")
            if (
                not isinstance(prepared, PreparedRAG)
                or not isinstance(answer, str) or not answer.strip()
                or state.get("tool_calls") != ()
            ):
                raise RAGGraphError("The RAG graph returned an invalid final state.")
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

    def start_stream(self, question: str | PreparedRAG) -> PreparedRAGStream:
        """Pause after retrieve update, before generation or StreamingResponse."""
        initial = _initial_state(question)
        control = StreamControl()
        run = PreparedRAGStream(
            self._events(initial, control),
            prepared=initial["prepared"], control=control,
        )
        if not initial["needs_retrieval"]:
            return run
        try:
            event = run.next_event()
            kind, data = _event_data(event)
            update = data.get("retrieve_node")
            if (
                kind != "updates" or set(data) != {"retrieve_node"}
                or not isinstance(update, dict)
            ):
                raise RAGGraphError("The RAG graph did not finish retrieval.")
            prepared = update.get("prepared")
            if not isinstance(prepared, PreparedRAG):
                raise RAGGraphError("The RAG graph returned no prepared context.")
            run.prepared = prepared
            return run
        except StopIteration as exc:
            run.close()
            raise RAGGraphError("The RAG graph did not finish retrieval.") from exc
        except BaseException:
            run.close()
            raise

    def stream(self, run: PreparedRAGStream) -> Iterator[str]:
        """Expose sanitized custom deltas only, requiring a final generate update."""
        finished = False
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
            if not finished or run.prepared is None:
                raise RAGGraphError("The RAG graph did not finish generation.")
        finally:
            run.close()
