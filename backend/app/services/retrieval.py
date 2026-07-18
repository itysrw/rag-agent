"""Tunable semantic retrieval orchestration with safe search logging."""

import hashlib
import json
from functools import lru_cache
from uuid import UUID

from loguru import logger

from backend.app.core.logging import JSONL_LOG_MARKER
from backend.app.services.embedding import EmbeddingClient, get_embedding_client
from backend.app.services.qdrant_store import (
    QdrantVectorStore,
    RetrievedChunk,
    get_qdrant_vector_store,
)

RETRIEVAL_TOP_K = 5
RETRIEVAL_TOP_K_MIN = 1
RETRIEVAL_TOP_K_MAX = 20
RETRIEVAL_SEARCH_EVENT = "retrieval_search_completed"


class RetrievalService:
    """Encode one query and retrieve a bounded number of Qdrant payloads."""

    def __init__(
        self,
        embedding_client: EmbeddingClient,
        vector_store: QdrantVectorStore,
    ) -> None:
        self._embedding_client = embedding_client
        self._vector_store = vector_store

    def search(
        self,
        query: str,
        *,
        top_k: int = RETRIEVAL_TOP_K,
        doc_id: UUID | None = None,
    ) -> list[RetrievedChunk]:
        """Return the most similar Chunks, optionally within one document."""
        validated_top_k = _validated_top_k(top_k)
        query_vector = self._embedding_client.embed_query(query)
        results = self._vector_store.search(
            query_vector,
            limit=validated_top_k,
            doc_id=doc_id,
        )
        _log_search_event(
            query=query,
            top_k=validated_top_k,
            doc_id=doc_id,
            results=results,
        )
        return results


def _validated_top_k(top_k: int) -> int:
    """Reject loose types and out-of-range limits before any model work."""
    if isinstance(top_k, bool) or not isinstance(top_k, int):
        raise ValueError("top_k must be an integer")
    if not RETRIEVAL_TOP_K_MIN <= top_k <= RETRIEVAL_TOP_K_MAX:
        raise ValueError(
            f"top_k must be between {RETRIEVAL_TOP_K_MIN} and {RETRIEVAL_TOP_K_MAX}"
        )
    return top_k


def _log_search_event(
    *,
    query: str,
    top_k: int,
    doc_id: UUID | None,
    results: list[RetrievedChunk],
) -> None:
    """Emit one single-line JSON event without raw query or chunk content."""
    event = {
        "event": RETRIEVAL_SEARCH_EVENT,
        "query_sha256": hashlib.sha256(query.encode("utf-8")).hexdigest(),
        "query_len": len(query),
        "top_k": top_k,
        "filter_doc_id": None if doc_id is None else str(doc_id),
        "result_count": len(results),
        "results": [
            {
                "rank": rank,
                "chunk_id": str(result.chunk_id),
                "doc_id": str(result.doc_id),
                "filename": result.filename,
                "page": result.page,
                "score": result.score,
            }
            for rank, result in enumerate(results, start=1)
        ],
    }
    try:
        message = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError):
        logger.error("Retrieval search event serialization failed.")
        return
    logger.bind(**{JSONL_LOG_MARKER: True}).info(message)


@lru_cache
def get_retrieval_service() -> RetrievalService:
    """Return the lazy process-wide retrieval service."""
    return RetrievalService(get_embedding_client(), get_qdrant_vector_store())
