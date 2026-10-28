"""Independent Day 11 Hybrid retrieval HTTP endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import ValidationError

from backend.app.api.retrieval import (
    RetrievalSearchRequest,
    RetrievalSearchResponse,
    RetrievedChunkResponse,
)
from backend.app.services.bm25 import (
    BM25Error,
    BM25IndexError,
    BM25UnavailableError,
)
from backend.app.services.embedding import EmbeddingError, EmbeddingInputTooLongError
from backend.app.services.hybrid import (
    HybridError,
    HybridResultError,
    HybridRetrievalService,
    get_hybrid_retrieval_service,
)
from backend.app.services.qdrant_store import (
    QdrantCollectionMismatchError,
    QdrantResultError,
    QdrantStoreError,
    QdrantUnavailableError,
)

router = APIRouter()


def require_hybrid_retrieval_service() -> HybridRetrievalService:
    """Resolve lazy branch clients without performing retrieval work."""
    try:
        return get_hybrid_retrieval_service()
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The hybrid retrieval service is unavailable.",
        ) from exc


@router.post(
    "/retrieval/hybrid/search",
    response_model=RetrievalSearchResponse,
)
def search_hybrid(
    request: RetrievalSearchRequest,
    service: Annotated[
        HybridRetrievalService,
        Depends(require_hybrid_retrieval_service),
    ],
) -> RetrievalSearchResponse:
    """Return vector and BM25 candidates fused by reciprocal rank."""
    try:
        results = service.search(
            request.query,
            top_k=request.top_k,
            doc_id=request.doc_id,
        )
    except EmbeddingInputTooLongError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The hybrid retrieval query exceeds the embedding model limit.",
        ) from exc
    except QdrantResultError as exc:
        logger.error("Hybrid vector result validation failed: {}", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The hybrid retrieval service returned an invalid result.",
        ) from exc
    except HybridResultError as exc:
        logger.error("Hybrid fusion result validation failed: {}", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The hybrid retrieval service returned an invalid result.",
        ) from exc
    except BM25UnavailableError as exc:
        logger.error("Hybrid BM25 corpus unavailable: {}", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The hybrid retrieval service is unavailable.",
        ) from exc
    except BM25IndexError as exc:
        logger.error("Hybrid BM25 index failed: {}", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The hybrid retrieval service failed.",
        ) from exc
    except EmbeddingError as exc:
        logger.error("Hybrid embedding failed: {}", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The hybrid retrieval service is unavailable.",
        ) from exc
    except (QdrantUnavailableError, QdrantCollectionMismatchError) as exc:
        logger.error("Hybrid vector store unavailable: {}", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The hybrid retrieval service is unavailable.",
        ) from exc
    except QdrantStoreError as exc:
        logger.error("Hybrid vector store failed: {}", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The hybrid retrieval service is unavailable.",
        ) from exc
    except BM25Error as exc:
        logger.error("Hybrid BM25 retrieval failed: {}", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The hybrid retrieval service failed.",
        ) from exc
    except HybridError as exc:
        logger.error("Hybrid fusion failed: {}", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The hybrid retrieval service failed.",
        ) from exc

    return RetrievalSearchResponse(
        results=[
            RetrievedChunkResponse.model_validate(result, from_attributes=True)
            for result in results
        ]
    )
