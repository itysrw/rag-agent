"""Independent Day 10 BM25 keyword-search HTTP endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from backend.app.api.retrieval import (
    RetrievalSearchRequest,
    RetrievalSearchResponse,
    RetrievedChunkResponse,
)
from backend.app.services.bm25 import (
    BM25Error,
    BM25IndexError,
    BM25Service,
    BM25UnavailableError,
    get_bm25_service,
)

router = APIRouter()


def require_bm25_service() -> BM25Service:
    """Resolve the process-local service without loading its PostgreSQL corpus."""
    return get_bm25_service()


@router.post(
    "/retrieval/bm25/search",
    response_model=RetrievalSearchResponse,
)
def search_bm25(
    request: RetrievalSearchRequest,
    service: Annotated[BM25Service, Depends(require_bm25_service)],
) -> RetrievalSearchResponse:
    """Return keyword-overlapping Chunks ranked by raw BM25 score."""
    try:
        results = service.search(
            request.query,
            top_k=request.top_k,
            doc_id=request.doc_id,
        )
    except BM25UnavailableError as exc:
        logger.error("BM25 corpus unavailable: {}", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The BM25 retrieval service is unavailable.",
        ) from exc
    except BM25IndexError as exc:
        logger.error("BM25 result validation failed: {}", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The BM25 retrieval service failed.",
        ) from exc
    except BM25Error as exc:
        logger.error("BM25 retrieval failed: {}", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The BM25 retrieval service failed.",
        ) from exc

    return RetrievalSearchResponse(
        results=[
            RetrievedChunkResponse.model_validate(result, from_attributes=True)
            for result in results
        ]
    )
