"""Fixed Top-5 Qdrant similarity-search HTTP endpoint."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

from backend.app.models.chunk import JSONScalar
from backend.app.services.embedding import (
    EmbeddingError,
    EmbeddingInputTooLongError,
)
from backend.app.services.qdrant_store import (
    QdrantCollectionMismatchError,
    QdrantResultError,
    QdrantStoreError,
    QdrantUnavailableError,
)
from backend.app.services.retrieval import (
    RETRIEVAL_TOP_K,
    RETRIEVAL_TOP_K_MAX,
    RETRIEVAL_TOP_K_MIN,
    RetrievalService,
    get_retrieval_service,
)

router = APIRouter()


class RetrievalSearchRequest(BaseModel):
    """One required query with an optional bounded limit and document filter."""

    model_config = ConfigDict(extra="forbid")

    query: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=4096),
    ]
    top_k: Annotated[
        int,
        Field(strict=True, ge=RETRIEVAL_TOP_K_MIN, le=RETRIEVAL_TOP_K_MAX),
    ] = RETRIEVAL_TOP_K
    doc_id: UUID | None = None


class RetrievedChunkResponse(BaseModel):
    """A safe Qdrant payload without its stored vector."""

    chunk_id: UUID
    doc_id: UUID
    chunk_index: int
    content: str
    page: int
    filename: str
    metadata: dict[str, JSONScalar]
    score: float


class RetrievalSearchResponse(BaseModel):
    """Fixed-limit semantic retrieval results."""

    results: list[RetrievedChunkResponse]


def require_retrieval_service() -> RetrievalService:
    """Resolve local retrieval configuration only when the route is called."""
    try:
        return get_retrieval_service()
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The retrieval service is unavailable.",
        ) from exc


@router.post("/retrieval/search", response_model=RetrievalSearchResponse)
def search_retrieval(
    request: RetrievalSearchRequest,
    service: Annotated[RetrievalService, Depends(require_retrieval_service)],
) -> RetrievalSearchResponse:
    """Return the most similar indexed Chunks for one user query."""
    try:
        results = service.search(
            request.query,
            top_k=request.top_k,
            doc_id=request.doc_id,
        )
    except EmbeddingInputTooLongError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The retrieval query exceeds the embedding model limit.",
        ) from exc
    except EmbeddingError as exc:
        logger.error("Retrieval embedding failed: {}", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The retrieval service is unavailable.",
        ) from exc
    except QdrantResultError as exc:
        logger.error("Retrieval result validation failed: {}", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The retrieval service returned an invalid result.",
        ) from exc
    except (QdrantUnavailableError, QdrantCollectionMismatchError) as exc:
        logger.error("Retrieval vector store unavailable: {}", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The retrieval service is unavailable.",
        ) from exc
    except QdrantStoreError as exc:
        logger.error("Retrieval vector store failed: {}", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The retrieval service is unavailable.",
        ) from exc

    return RetrievalSearchResponse(
        results=[RetrievedChunkResponse.model_validate(result, from_attributes=True) for result in results]
    )
