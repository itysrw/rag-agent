"""Knowledge-base RAG chat endpoint with complete and SSE responses."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated
from uuid import UUID
import asyncio

import anyio
from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel, StringConstraints, ValidationError
from starlette.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool
from starlette.requests import ClientDisconnect
from starlette.types import Receive, Scope, Send

from backend.app.services.embedding import (
    EmbeddingError,
    EmbeddingInputTooLongError,
)
from backend.app.services.bm25 import BM25Error, BM25UnavailableError
from backend.app.services.document_catalog import DocumentCatalogError, DocumentCatalogUnavailableError
from backend.app.services.hybrid import HybridError, HybridResultError
from backend.app.services.reranker import (
    RerankerError,
    RerankerInputError,
    RerankerResultError,
    RerankerUnavailableError,
)
from backend.app.services.llm import (
    LLMConfigurationError,
    LLMServiceError,
)
from backend.app.services.qdrant_store import (
    QdrantCollectionMismatchError,
    QdrantResultError,
    QdrantStoreError,
    QdrantUnavailableError,
)
from backend.app.services.rag import (
    RAGGraphError,
    RAGService,
    RAGSource,
    get_rag_service,
)
from backend.app.services.request_trace import TraceRecorder, RequestTraceStore, get_request_trace_store

if TYPE_CHECKING:
    from backend.app.agent.service import PreparedRAGStream

from backend.app.services.conversation_memory import (
    ConversationBusyError, ConversationMemoryError, ConversationMemoryUnavailableError,
    ConversationNotFoundError,
)

router = APIRouter()


class ChatRequest(BaseModel):
    """One user message and the desired response mode."""

    message: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=4096),
    ]
    stream: bool = False
    session_id: UUID | None = None


class ChatSourceResponse(BaseModel):
    """One backend-derived document source."""

    filename: str
    page: int


class ChatResponse(BaseModel):
    """Complete RAG answer with structured sources."""

    answer: str
    model: str
    sources: list[ChatSourceResponse]
    session_id: UUID


def require_rag_service() -> RAGService:
    """Resolve RAG dependencies only when the chat route is called."""
    try:
        return get_rag_service()
    except LLMConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The language model is not configured.",
        ) from exc
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The RAG service is unavailable.",
        ) from exc


@dataclass(slots=True)
class _StreamTraceState:
    done: bool = False
    error_code: str | None = None


def _is_client_disconnect(exc: BaseException) -> bool:
    if isinstance(exc, (OSError, asyncio.CancelledError, ClientDisconnect)):
        return True
    if isinstance(exc, BaseExceptionGroup):
        return bool(exc.exceptions) and all(_is_client_disconnect(item) for item in exc.exceptions)
    return False


def stream_sse(
    service: RAGService, run: PreparedRAGStream,
    trace_state: _StreamTraceState | None = None,
) -> Iterator[str]:
    """Encode RAG deltas and backend-derived sources as SSE events."""
    deltas = service.stream(run)
    try:
        for delta in deltas:
            payload = json.dumps({"delta": delta}, ensure_ascii=False)
            yield f"data: {payload}\n\n"
        if run.prepared is None:
            raise RAGGraphError("The RAG graph returned no prepared context.")
        sources_payload = json.dumps(
            {"sources": [_source_dict(source) for source in run.prepared.sources]},
            ensure_ascii=False,
        )
        yield f"event: sources\ndata: {sources_payload}\n\n"
        yield "data: [DONE]\n\n"
        if trace_state is not None:
            trace_state.done = True
    except LLMServiceError as exc:
        if trace_state is not None:
            trace_state.error_code = "llm_stream_failed"
        logger.error("RAG language model stream failed: {}", type(exc).__name__)
        payload = json.dumps(
            {"detail": "The language model stream failed."},
            ensure_ascii=False,
        )
        yield f"event: error\ndata: {payload}\n\n"
    except RAGGraphError:
        if trace_state is not None:
            trace_state.error_code = "graph_stream_failed"
        logger.error("RAG graph stream failed")
        payload = json.dumps({"detail": "The RAG stream failed."}, ensure_ascii=False)
        yield f"event: error\ndata: {payload}\n\n"
    except ConversationMemoryError:
        if trace_state is not None:
            trace_state.error_code = "conversation_save_failed"
        logger.error("Conversation memory stream save failed")
        payload = json.dumps({"detail": "The conversation could not be saved."})
        yield f"event: error\ndata: {payload}\n\n"
    finally:
        close = getattr(deltas, "close", None)
        if callable(close):
            close()
        run.close()


class _RAGStreamingResponse(StreamingResponse):
    """Close the prefetched graph even when ASGI delivery is cancelled."""

    def __init__(
        self, service: RAGService, run: PreparedRAGStream,
        trace: TraceRecorder | None = None, store: RequestTraceStore | None = None,
    ) -> None:
        self._run = run
        self._trace = trace
        self._store = store
        self._trace_state = _StreamTraceState()
        super().__init__(
            stream_sse(service, run, self._trace_state),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no",
                     "X-Session-ID": str(run.session_id)},
        )

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        failure: BaseException | None = None
        try:
            await super().__call__(scope, receive, send)
        except BaseException as exc:
            failure = exc
            raise
        finally:
            self._run.cancel()
            with anyio.CancelScope(shield=True):
                try:
                    await run_in_threadpool(self._run.close)
                except RAGGraphError:
                    logger.error("RAG graph stream cleanup failed")
                if self._trace is not None and self._store is not None:
                    error_code = self._trace_state.error_code
                    if error_code is not None:
                        outcome = "error"
                    elif failure is None and self._trace_state.done:
                        outcome = "success"
                    elif failure is not None and not _is_client_disconnect(failure):
                        outcome, error_code = "error", "stream_failed"
                    else:
                        outcome, error_code = "cancelled", "client_disconnected"
                    await run_in_threadpool(
                        self._trace.finish, self._store,
                        outcome=outcome, http_status=200, error_code=error_code,
                    )


def _handle_chat(
    request: ChatRequest,
    service: RAGService,
    trace: TraceRecorder,
    store: RequestTraceStore,
) -> ChatResponse | StreamingResponse:
    """Retrieve before returning either a complete answer or SSE stream."""
    try:
        if request.stream:
            if isinstance(service, RAGService):
                run = service.start_stream(request.message, session_id=request.session_id, trace=trace)
            else:
                run = service.start_stream(request.message, session_id=request.session_id)
        else:
            if isinstance(service, RAGService):
                answer = service.complete(request.message, session_id=request.session_id, trace=trace)
            else:
                answer = service.complete(request.message, session_id=request.session_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(404, "The conversation does not exist.") from exc
    except ConversationBusyError as exc:
        raise HTTPException(409, "The conversation already has a request in progress.") from exc
    except ConversationMemoryUnavailableError as exc:
        raise HTTPException(503, "The conversation memory is unavailable.") from exc
    except ConversationMemoryError as exc:
        raise HTTPException(500, "The conversation memory request failed.") from exc
    except EmbeddingInputTooLongError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The chat message exceeds the embedding model limit.",
        ) from exc
    except EmbeddingError as exc:
        logger.error("RAG embedding failed: {}", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The retrieval service is unavailable.",
        ) from exc
    except QdrantResultError as exc:
        logger.error("RAG retrieval result invalid: {}", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The retrieval service returned an invalid result.",
        ) from exc
    except (QdrantUnavailableError, QdrantCollectionMismatchError) as exc:
        logger.error("RAG vector store unavailable: {}", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The retrieval service is unavailable.",
        ) from exc
    except QdrantStoreError as exc:
        logger.error("RAG vector store failed: {}", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The retrieval service is unavailable.",
        ) from exc
    except RerankerInputError as exc:
        raise HTTPException(422, "The chat message exceeds the reranker model limit.") from exc
    except (HybridResultError, RerankerResultError) as exc:
        raise HTTPException(502, "The retrieval service returned an invalid result.") from exc
    except (BM25UnavailableError, RerankerUnavailableError) as exc:
        raise HTTPException(503, "The retrieval service is unavailable.") from exc
    except (BM25Error, HybridError, RerankerError) as exc:
        raise HTTPException(500, "The retrieval service failed.") from exc
    except DocumentCatalogUnavailableError as exc:
        raise HTTPException(503, "The document catalog is unavailable.") from exc
    except DocumentCatalogError as exc:
        raise HTTPException(500, "The document catalog service failed.") from exc
    except RAGGraphError as exc:
        logger.error("RAG graph failed")
        raise HTTPException(500, "The RAG service failed.") from exc
    except LLMServiceError as exc:
        logger.error("RAG language model request failed: {}", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The language model request failed.",
        ) from exc

    if request.stream:
        return _RAGStreamingResponse(service, run, trace, store)

    return ChatResponse(
        answer=answer.answer,
        model=answer.model,
        session_id=answer.session_id,
        sources=[
            ChatSourceResponse(filename=source.filename, page=source.page)
            for source in answer.sources
        ],
    )


@router.post("/chat", response_model=None)
def chat(
    request: ChatRequest,
    service: Annotated[RAGService, Depends(require_rag_service)],
) -> ChatResponse | StreamingResponse:
    """Record one validated business request without changing its public schema."""
    trace = TraceRecorder(
        request.message, mode="sse" if request.stream else "json",
        session_id=request.session_id, model=service.model,
    )
    store = get_request_trace_store()
    try:
        result = _handle_chat(request, service, trace, store)
    except HTTPException as exc:
        cause = exc.__cause__
        code = type(cause).__name__ if cause is not None else f"http_{exc.status_code}"
        trace.finish(store, outcome="error", http_status=exc.status_code, error_code=code)
        raise
    except BaseException:
        trace.finish(store, outcome="error", http_status=500, error_code="internal_error")
        raise
    if not request.stream:
        trace.finish(store, outcome="success", http_status=200)
    return result


def _source_dict(source: RAGSource) -> dict[str, str | int]:
    return {"filename": source.filename, "page": source.page}
