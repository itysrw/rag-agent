"""Request-scoped chat evidence and best-effort relational persistence."""

from datetime import datetime
from threading import Lock
from time import perf_counter
from typing import Literal
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.database import get_session_factory
from backend.app.models.document import utc_now
from backend.app.models.request_log import RequestLog
from backend.app.services.llm import TOOL_NAMES, AgentToolCall, ModelUsage
from backend.app.services.rag import RAGSource
from backend.app.services.reranker import RerankedChunk

TraceOutcome = Literal["success", "error", "cancelled"]


class RequestTraceStore:
    """Use a separate short transaction for each trace and admin read."""

    def __init__(self, sessions: sessionmaker[Session] | None = None) -> None:
        self._sessions = sessions

    def _session_factory(self) -> sessionmaker[Session]:
        return self._sessions or get_session_factory()

    def save(self, values: dict[str, object]) -> None:
        """Insert exactly one row using the recorder's stable trace ID."""
        with self._session_factory().begin() as session:
            session.add(RequestLog(**values))

    def recent(self, limit: int) -> list[RequestLog]:
        """Return a stable newest-first page without loading conversation data."""
        with self._session_factory()() as session:
            return list(session.scalars(
                select(RequestLog).order_by(RequestLog.created_at.desc(), RequestLog.id.desc()).limit(limit)
            ))


def get_request_trace_store() -> RequestTraceStore:
    """Construct a lazy store; application startup never connects to PostgreSQL."""
    return RequestTraceStore()


class TraceRecorder:
    """Collect one chat turn without putting mutable data on shared services."""

    def __init__(
        self, query: str, *, mode: Literal["json", "sse"],
        session_id: UUID | None = None, model: str | None = None,
    ) -> None:
        self.id = uuid4()
        self.created_at = utc_now()
        self._started = perf_counter()
        self._lock = Lock()
        self._finished = False
        self.query = query
        self.mode = mode
        self.session_id = session_id
        self.model = model
        self.standalone_query: str | None = None
        self.answer: str | None = None
        self.sources: list[dict[str, object]] = []
        self.tool_calls: list[dict[str, object]] = []
        self.retrieved_docs: list[dict[str, object]] = []
        self.model_calls: list[dict[str, object]] = []
        self.business_committed = False

    def record_session(self, session_id: UUID) -> None:
        with self._lock:
            self.session_id = session_id

    def record_standalone_query(self, query: str) -> None:
        with self._lock:
            self.standalone_query = query

    def begin_model_call(self, stage: str) -> int:
        """Reserve a stage before the provider request, including failed calls."""
        with self._lock:
            index = len(self.model_calls)
            self.model_calls.append({"stage": stage, "prompt_tokens": None, "completion_tokens": None})
            return index

    def record_model_usage(self, index: int, usage: ModelUsage) -> None:
        with self._lock:
            self.model_calls[index]["prompt_tokens"] = usage.prompt_tokens
            self.model_calls[index]["completion_tokens"] = usage.completion_tokens

    def record_tool_selection(self, call: AgentToolCall) -> None:
        with self._lock:
            self.tool_calls.append({"name": call["name"], "call_id": call["call_id"], "status": "selected"})

    def record_tool_result(self, *, succeeded: bool) -> None:
        with self._lock:
            if self.tool_calls:
                self.tool_calls[-1]["status"] = "success" if succeeded else "error"

    def successful_tool_name(self) -> str | None:
        """Expose the single successful tool's public name before trace persistence."""
        with self._lock:
            if len(self.tool_calls) != 1 or self.tool_calls[0]["status"] != "success":
                return None
            name = self.tool_calls[0]["name"]
            return name if isinstance(name, str) and name in TOOL_NAMES else None

    def record_retrieval(
        self, chunks: tuple[RerankedChunk, ...], included_ids: frozenset[UUID],
    ) -> None:
        """Persist only identities and scores from the tool's ranked candidates."""
        with self._lock:
            self.retrieved_docs = [
                {"chunk_id": str(chunk.chunk_id), "doc_id": str(chunk.doc_id),
                 "filename": chunk.filename, "page": chunk.page, "rank": chunk.rerank_rank,
                 "vector_score": chunk.vector_score, "reranker_score": chunk.score,
                 "included_in_context": chunk.chunk_id in included_ids}
                for chunk in chunks
            ]

    def record_answer(self, answer: str, sources: tuple[RAGSource, ...]) -> None:
        with self._lock:
            self.answer = answer
            self.sources = [{"filename": source.filename, "page": source.page} for source in sources]

    def mark_committed(self) -> None:
        with self._lock:
            self.business_committed = True

    def finish(
        self, store: RequestTraceStore, *, outcome: TraceOutcome,
        http_status: int, error_code: str | None = None,
    ) -> None:
        """Finalize once; a trace-store outage never replaces the chat outcome."""
        with self._lock:
            if self._finished:
                return
            self._finished = True
            complete = all(
                call["prompt_tokens"] is not None and call["completion_tokens"] is not None
                for call in self.model_calls
            )
            values: dict[str, object] = {
                "id": self.id, "created_at": self.created_at, "finished_at": utc_now(),
                "session_id": self.session_id, "mode": self.mode, "model": self.model,
                "query": self.query, "standalone_query": self.standalone_query,
                "answer": self.answer, "tool_calls": self.tool_calls,
                "retrieved_docs": self.retrieved_docs, "sources": self.sources,
                "model_calls": self.model_calls,
                "prompt_tokens": sum(int(call["prompt_tokens"]) for call in self.model_calls) if complete else None,
                "completion_tokens": sum(int(call["completion_tokens"]) for call in self.model_calls) if complete else None,
                "usage_complete": complete, "latency_ms": (perf_counter() - self._started) * 1000,
                "outcome": outcome, "http_status": http_status, "error_code": error_code,
                "business_committed": self.business_committed,
            }
        try:
            store.save(values)
        except Exception as exc:
            logger.error("Chat trace persistence failed: {}", type(exc).__name__)
