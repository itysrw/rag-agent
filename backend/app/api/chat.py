"""Knowledge-base RAG chat endpoint with complete and SSE responses."""

import json
from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel, StringConstraints, ValidationError
from starlette.responses import StreamingResponse

from backend.app.services.embedding import (
    EmbeddingError,
    EmbeddingInputTooLongError,
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
    PreparedRAG,
    RAGService,
    RAGSource,
    get_rag_service,
)

router = APIRouter()


class ChatRequest(BaseModel):
    """One user message and the desired response mode."""

    message: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=4096),
    ]
    stream: bool = False


class ChatSourceResponse(BaseModel):
    """One backend-derived document source."""

    filename: str
    page: int


class ChatResponse(BaseModel):
    """Complete RAG answer with structured sources."""

    answer: str
    model: str
    sources: list[ChatSourceResponse]


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


def stream_sse(service: RAGService, prepared: PreparedRAG) -> Iterator[str]:
    """Encode RAG deltas and backend-derived sources as SSE events."""
    try:
        for delta in service.stream(prepared):
            payload = json.dumps({"delta": delta}, ensure_ascii=False)
            yield f"data: {payload}\n\n"
        sources_payload = json.dumps(
            {"sources": [_source_dict(source) for source in prepared.sources]},
            ensure_ascii=False,
        )
        yield f"event: sources\ndata: {sources_payload}\n\n"
        yield "data: [DONE]\n\n"
    except LLMServiceError:
        logger.exception("RAG language model stream failed")
        payload = json.dumps(
            {"detail": "The language model stream failed."},
            ensure_ascii=False,
        )
        yield f"event: error\ndata: {payload}\n\n"


@router.post("/chat", response_model=None)
def chat(
    request: ChatRequest,
    service: Annotated[RAGService, Depends(require_rag_service)],
) -> ChatResponse | StreamingResponse:
    """Retrieve before returning either a complete answer or SSE stream."""
    try:
        prepared = service.prepare(request.message)
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

    if request.stream:
        return StreamingResponse(
            stream_sse(service, prepared),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    try:
        answer = service.complete(prepared)
    except LLMServiceError as exc:
        logger.exception("RAG language model request failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The language model request failed.",
        ) from exc

    return ChatResponse(
        answer=answer.answer,
        model=answer.model,
        sources=[
            ChatSourceResponse(filename=source.filename, page=source.page)
            for source in answer.sources
        ],
    )


def _source_dict(source: RAGSource) -> dict[str, str | int]:
    return {"filename": source.filename, "page": source.page}
