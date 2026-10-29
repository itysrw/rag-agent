"""Fixed Hybrid Top-20 to Rerank Top-5 debugging endpoint."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, StringConstraints, ValidationError

from backend.app.api.retrieval import RetrievedChunkResponse
from backend.app.services.bm25 import BM25Error, BM25UnavailableError
from backend.app.services.embedding import EmbeddingError, EmbeddingInputTooLongError
from backend.app.services.hybrid import HybridError, HybridResultError
from backend.app.services.qdrant_store import QdrantResultError, QdrantStoreError
from backend.app.services.reranker import (
    RerankedRetrievalService,
    RerankerError,
    RerankerInputError,
    RerankerResultError,
    RerankerUnavailableError,
    get_reranked_retrieval_service,
)

router = APIRouter()


class RerankSearchRequest(BaseModel):
    """No caller-controlled candidate depth or output count."""

    model_config = ConfigDict(extra="forbid")
    query: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4096)]
    doc_id: UUID | None = None


class RerankedChunkResponse(RetrievedChunkResponse):
    """Raw reranker logit with public before/after ranking evidence."""

    hybrid_rank: int
    rerank_rank: int
    rank_change: int


class RerankSearchResponse(BaseModel):
    """At most five candidates; internal vector evidence stays private."""

    results: list[RerankedChunkResponse]


def require_reranked_retrieval_service() -> RerankedRetrievalService:
    """Resolve settings lazily and hide invalid local configuration."""
    try:
        return get_reranked_retrieval_service()
    except ValidationError as exc:
        raise HTTPException(503, "The rerank retrieval service is unavailable.") from exc


@router.post("/retrieval/rerank/search", response_model=RerankSearchResponse)
def search_reranked(
    request: RerankSearchRequest,
    service: Annotated[RerankedRetrievalService, Depends(require_reranked_retrieval_service)],
) -> RerankSearchResponse:
    """Execute the complete fixed retrieval pipeline."""
    try:
        outcome = service.search(request.query, doc_id=request.doc_id)
    except (EmbeddingInputTooLongError, RerankerInputError) as exc:
        raise HTTPException(422, "The rerank query exceeds the model input limit.") from exc
    except (QdrantResultError, HybridResultError, RerankerResultError) as exc:
        raise HTTPException(502, "The rerank retrieval service returned an invalid result.") from exc
    except (EmbeddingError, QdrantStoreError, BM25UnavailableError, RerankerUnavailableError) as exc:
        raise HTTPException(503, "The rerank retrieval service is unavailable.") from exc
    except (BM25Error, HybridError, RerankerError) as exc:
        raise HTTPException(500, "The rerank retrieval service failed.") from exc
    return RerankSearchResponse(results=[
        RerankedChunkResponse.model_validate(item, from_attributes=True)
        for item in outcome.results
    ])
