"""Execute a single existing RAG graph and capture its actual evidence."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from threading import Lock
from time import perf_counter
from typing import Protocol, cast
from uuid import NAMESPACE_URL, uuid5

from openai import APITimeoutError, AuthenticationError, PermissionDeniedError, RateLimitError

from backend.app.agent.graph import build_rag_graph
from backend.app.agent.service import RAGGraphRunner
from backend.app.core.config import ConversationMemorySettings, RAGSettings, RAG_MIN_RELEVANCE_SCORE
from backend.app.services.bm25 import BM25Error, BM25UnavailableError
from backend.app.services.document_catalog import DocumentCatalogError, DocumentCatalogService
from backend.app.services.embedding import EmbeddingError, ModelDownloadError, ModelLoadError
from backend.app.services.hybrid import HybridError
from backend.app.services.qdrant_store import QdrantCollectionMismatchError, QdrantStoreError, QdrantUnavailableError
from backend.app.services.llm import (
    AgentToolCall, LLMClient, LLMMessage, LLMServiceError, LLMToolCallError, LLMToolDefinition,
)
from backend.app.services.rag import RAGAnswer, RAGSource, build_sources, select_relevant_chunks
from backend.app.services.reranker import (
    RerankOutcome, RerankedChunk, RerankedRetrievalService, RerankerError, RerankerUnavailableError,
)

SEARCH_TOOL = "search_knowledge_base"
MAX_LLM_REQUESTS = 100


class EvalStop(RuntimeError):
    """A safe error code that stops the run."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class RequestBudget:
    """Count attempts before the HTTP transport can send them."""

    def __init__(self, limit: int) -> None:
        if type(limit) is not int or not 1 <= limit <= MAX_LLM_REQUESTS:
            raise ValueError("The request budget must be between 1 and 100.")
        self.limit = limit
        self.attempts = 0
        self._lock = Lock()

    def consume(self) -> None:
        """Reserve an attempt, including requests that time out or fail."""
        with self._lock:
            if self.attempts >= self.limit:
                raise EvalStop("budget_exhausted")
            self.attempts += 1


@dataclass(frozen=True, slots=True)
class Candidate:
    chunk_id: str
    filename: str
    page: int
    rank: int
    included_in_context: bool


@dataclass(frozen=True, slots=True)
class Observation:
    answer: RAGAnswer | None
    selected_tool: str | None
    retrieved_chunks: tuple[Candidate, ...] | None
    latency_ms: float
    error_code: str | None = None
    stop_run: bool = False


class EvalLLM(Protocol):
    @property
    def model(self) -> str: ...

    def select_tool(
        self, messages: Sequence[LLMMessage], tools: Sequence[LLMToolDefinition],
    ) -> AgentToolCall: ...

    def complete_messages(self, messages: Sequence[LLMMessage]) -> str: ...


class _Capture:
    """Expose the dependency methods used by a complete turn with empty history."""

    def __init__(
        self, llm: EvalLLM, search: Callable[[str], RerankOutcome], settings: RAGSettings,
    ) -> None:
        self.llm = llm
        self.retrieve = search
        self.settings = settings
        self.reset()

    def reset(self) -> None:
        self.selected_tool: str | None = None
        self.chunks: tuple[Candidate, ...] | None = None
        self.context_sources: tuple[RAGSource, ...] = ()

    def select_tool(
        self, messages: Sequence[LLMMessage], tools: Sequence[LLMToolDefinition],
    ) -> AgentToolCall:
        call = self.llm.select_tool(messages, tools)
        self.selected_tool = call["name"]
        return call

    def complete_messages(self, messages: Sequence[LLMMessage]) -> str:
        return self.llm.complete_messages(messages)

    def search(self, query: str) -> RerankOutcome:
        if self.chunks is not None:
            raise EvalStop("repeated_retrieval")
        outcome = self.retrieve(query)
        relevant = select_relevant_chunks(outcome.results, min_score=self.settings.min_relevance_score)
        included_ids = {chunk.chunk_id for chunk in relevant}
        self.chunks = tuple(
            Candidate(str(chunk.chunk_id), chunk.filename, chunk.page, chunk.rerank_rank,
                      chunk.chunk_id in included_ids)
            for chunk in outcome.results
        )
        self.context_sources = build_sources(relevant)
        return outcome

    def verify(self, answer: RAGAnswer) -> None:
        if self.selected_tool == SEARCH_TOOL:
            if self.chunks is None or answer.sources != self.context_sources:
                raise EvalStop("evidence_mismatch")
        elif self.selected_tool is None or self.chunks is not None or answer.sources:
            raise EvalStop("evidence_mismatch")


def _classify_error(error: Exception, selected_tool: str | None) -> tuple[str, bool]:
    cause: BaseException | None = error
    while cause is not None:
        if isinstance(cause, EvalStop):
            return cause.code, True
        if isinstance(cause, (AuthenticationError, PermissionDeniedError)):
            return "invalid_credentials", True
        if isinstance(cause, RateLimitError):
            return "upstream_rate_limited", True
        if isinstance(cause, (APITimeoutError, TimeoutError)):
            return "upstream_timeout", False
        cause = cause.__cause__
    if isinstance(error, LLMToolCallError):
        return "tool_selection_failed", False
    if isinstance(error, LLMServiceError):
        return ("tool_selection_failed" if selected_tool is None else "generation_failed"), False
    if isinstance(error, (ModelDownloadError, ModelLoadError, RerankerUnavailableError,
                          QdrantUnavailableError, QdrantCollectionMismatchError, BM25UnavailableError)):
        return "retrieval_unavailable", True
    if isinstance(error, (EmbeddingError, RerankerError, QdrantStoreError, BM25Error, HybridError)):
        return "retrieval_failed", False
    if isinstance(error, DocumentCatalogError):
        return "catalog_failed", False
    if isinstance(error, MemoryError):
        return "memory_exhausted", True
    return "execution_failed", False


class EvalAgent:
    """Run one question without opening a business conversation."""

    def __init__(
        self,
        llm: EvalLLM,
        search: Callable[[str], RerankOutcome],
        settings: RAGSettings,
        *,
        catalog_factory: Callable[[], DocumentCatalogService],
        clock: Callable[[], float] = perf_counter,
    ) -> None:
        self.model = llm.model
        self._capture = _Capture(llm, search, settings)
        self._clock = clock
        graph = build_rag_graph(
            cast(RerankedRetrievalService, self._capture), cast(LLMClient, self._capture),
            settings, catalog_factory=catalog_factory,
            memory_settings=ConversationMemorySettings(
                _env_file=None, max_turns=5, max_tokens=2000, encoding_name="o200k_base",
            ),
        )
        self._runner = RAGGraphRunner(graph, self.model)

    def run(self, question: str) -> Observation:
        """Time the graph call and retain any evidence collected before a failure."""
        self._capture.reset()
        started = self._clock()
        answer = None
        failure: Exception | None = None
        interrupted = False
        try:
            answer = self._runner.complete(question, history=())
        except KeyboardInterrupt:
            interrupted = True
        except Exception as exc:
            failure = exc
        latency_ms = (self._clock() - started) * 1000
        if answer is not None:
            try:
                self._capture.verify(answer)
            except EvalStop as exc:
                failure = exc
                answer = None
        error_code, stop_run = (None, False)
        if interrupted:
            error_code, stop_run = "interrupted", True
        elif failure is not None:
            error_code, stop_run = _classify_error(failure, self._capture.selected_tool)
        return Observation(
            answer, self._capture.selected_tool, self._capture.chunks, latency_ms, error_code, stop_run,
        )


@dataclass(frozen=True, slots=True)
class MockResponse:
    """Canned answer and synthetic (filename, page, vector score) candidates."""

    answer: str
    candidates: tuple[tuple[str, int, float], ...]


class _MockLLM:
    model = "day18-mock"

    def __init__(self, responses: Mapping[str, MockResponse]) -> None:
        self.responses = responses
        self.answer = ""

    def select_tool(
        self, messages: Sequence[LLMMessage], tools: Sequence[LLMToolDefinition],
    ) -> AgentToolCall:
        question = messages[-1]["content"]
        self.answer = self.responses[question].answer
        return {"call_id": "mock-search", "name": SEARCH_TOOL, "arguments": {"query": question}}

    def complete_messages(self, messages: Sequence[LLMMessage]) -> str:
        return self.answer


def _disabled_catalog() -> DocumentCatalogService:
    raise EvalStop("mock_catalog_unavailable")


def build_mock_agent(responses: Mapping[str, MockResponse]) -> EvalAgent:
    """Build the real graph with in-memory, deterministic dependencies."""
    def search(question: str) -> RerankOutcome:
        chunks = tuple(
            RerankedChunk(
                chunk_id=uuid5(NAMESPACE_URL, f"day18:{question}:{rank}"),
                doc_id=uuid5(NAMESPACE_URL, f"day18:{filename}"),
                chunk_index=rank - 1, content="离线模拟证据", page=page, filename=filename,
                metadata={}, score=1.0, hybrid_score=0.03, hybrid_rank=rank,
                rerank_rank=rank, rank_change=0, vector_score=vector_score,
                vector_rank=rank, bm25_rank=None,
            )
            for rank, (filename, page, vector_score) in enumerate(responses[question].candidates, 1)
        )
        return RerankOutcome(chunks, (), len(chunks), 0)

    return EvalAgent(
        _MockLLM(responses), search,
        RAGSettings(_env_file=None, min_relevance_score=RAG_MIN_RELEVANCE_SCORE),
        catalog_factory=_disabled_catalog,
    )
