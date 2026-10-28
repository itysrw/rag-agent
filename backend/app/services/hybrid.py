"""Day 11 rank-only fusion for vector and BM25 retrieval results."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from uuid import UUID

from loguru import logger

from backend.app.core.logging import JSONL_LOG_MARKER
from backend.app.models.chunk import JSONScalar
from backend.app.services.bm25 import (
    BM25RetrievedChunk,
    BM25Service,
    get_bm25_service,
)
from backend.app.services.qdrant_store import RetrievedChunk
from backend.app.services.retrieval import (
    RETRIEVAL_TOP_K,
    RETRIEVAL_TOP_K_MAX,
    RETRIEVAL_TOP_K_MIN,
    RetrievalService,
    get_retrieval_service,
)

RRF_RANK_CONSTANT = 60
HYBRID_CANDIDATE_K = RETRIEVAL_TOP_K_MAX
HYBRID_SEARCH_EVENT = "hybrid_search_completed"


class HybridError(RuntimeError):
    """Base class for safe Hybrid retrieval failures."""


class HybridResultError(HybridError):
    """Raised for duplicate identities or inconsistent cross-store payloads."""


@dataclass(frozen=True, slots=True)
class HybridRetrievedChunk:
    """One fused Chunk whose public score is its reciprocal-rank score."""

    chunk_id: UUID
    doc_id: UUID
    chunk_index: int
    content: str
    page: int
    filename: str
    metadata: dict[str, JSONScalar]
    score: float
    vector_rank: int | None
    bm25_rank: int | None


@dataclass(frozen=True, slots=True)
class _RankedPayload:
    """One validated branch payload and its one-based rank."""

    chunk_id: UUID
    doc_id: UUID
    chunk_index: int
    content: str
    page: int
    filename: str
    metadata: dict[str, JSONScalar]
    rank: int


def reciprocal_rank_fusion(
    vector_results: Sequence[RetrievedChunk],
    bm25_results: Sequence[BM25RetrievedChunk],
    *,
    top_k: int,
    rank_constant: int = RRF_RANK_CONSTANT,
) -> list[HybridRetrievedChunk]:
    """Fuse two ranked lists by Chunk UUID without using branch scores."""
    validated_top_k = _validated_top_k(top_k)
    validated_rank_constant = _validated_rank_constant(rank_constant)
    vector_by_id = _ranked_branch(vector_results, branch_name="vector")
    bm25_by_id = _ranked_branch(bm25_results, branch_name="bm25")

    fused: list[HybridRetrievedChunk] = []
    for chunk_id in vector_by_id.keys() | bm25_by_id.keys():
        vector_item = vector_by_id.get(chunk_id)
        bm25_item = bm25_by_id.get(chunk_id)
        payload = vector_item or bm25_item
        if payload is None:  # pragma: no cover - set union guarantees a value
            raise HybridError("The Hybrid fusion state is invalid.")
        if (
            vector_item is not None
            and bm25_item is not None
            and not _same_payload(vector_item, bm25_item)
        ):
            raise HybridResultError(
                "The vector and BM25 Chunk payloads do not match."
            )

        vector_rank = None if vector_item is None else vector_item.rank
        bm25_rank = None if bm25_item is None else bm25_item.rank
        score = sum(
            1.0 / (validated_rank_constant + rank)
            for rank in (vector_rank, bm25_rank)
            if rank is not None
        )
        if not math.isfinite(score):
            raise HybridError("The Hybrid RRF score is invalid.")
        fused.append(
            HybridRetrievedChunk(
                chunk_id=payload.chunk_id,
                doc_id=payload.doc_id,
                chunk_index=payload.chunk_index,
                content=payload.content,
                page=payload.page,
                filename=payload.filename,
                metadata=dict(payload.metadata),
                score=score,
                vector_rank=vector_rank,
                bm25_rank=bm25_rank,
            )
        )

    fused.sort(
        key=lambda item: (
            -item.score,
            _best_rank(item),
            str(item.doc_id),
            item.chunk_index,
            str(item.chunk_id),
        )
    )
    return fused[:validated_top_k]


class HybridRetrievalService:
    """Run both existing retrieval branches and fuse their ranks."""

    def __init__(
        self,
        vector_service: RetrievalService,
        bm25_service: BM25Service,
    ) -> None:
        self._vector_service = vector_service
        self._bm25_service = bm25_service

    def search(
        self,
        query: str,
        *,
        top_k: int = RETRIEVAL_TOP_K,
        doc_id: UUID | None = None,
    ) -> list[HybridRetrievedChunk]:
        """Return the final Top-K after two fixed-depth synchronous searches."""
        validated_top_k = _validated_top_k(top_k)
        if not isinstance(query, str) or not query.strip() or len(query) > 4096:
            raise ValueError("query must contain between 1 and 4096 characters")
        if doc_id is not None and not isinstance(doc_id, UUID):
            raise ValueError("doc_id must be a UUID or None")

        vector_results = self._vector_service.search(
            query,
            top_k=HYBRID_CANDIDATE_K,
            doc_id=doc_id,
        )
        bm25_results = self._bm25_service.search(
            query,
            top_k=HYBRID_CANDIDATE_K,
            doc_id=doc_id,
        )
        results = reciprocal_rank_fusion(
            vector_results,
            bm25_results,
            top_k=validated_top_k,
        )
        _log_search_event(
            query=query,
            top_k=validated_top_k,
            doc_id=doc_id,
            vector_result_count=len(vector_results),
            bm25_result_count=len(bm25_results),
            results=results,
        )
        return results


def _ranked_branch(
    results: Sequence[RetrievedChunk] | Sequence[BM25RetrievedChunk],
    *,
    branch_name: str,
) -> dict[UUID, _RankedPayload]:
    ranked: dict[UUID, _RankedPayload] = {}
    for rank, result in enumerate(results, start=1):
        payload = _validated_payload(result, rank=rank)
        if payload.chunk_id in ranked:
            raise HybridResultError(
                f"The {branch_name} branch returned a duplicate Chunk identity."
            )
        ranked[payload.chunk_id] = payload
    return ranked


def _validated_payload(result: Any, *, rank: int) -> _RankedPayload:
    try:
        chunk_id = result.chunk_id
        doc_id = result.doc_id
        chunk_index = result.chunk_index
        content = result.content
        page = result.page
        filename = result.filename
        metadata = result.metadata
    except AttributeError as exc:
        raise HybridResultError(
            "A retrieval branch returned an invalid Chunk payload."
        ) from exc

    if not isinstance(chunk_id, UUID) or not isinstance(doc_id, UUID):
        raise HybridResultError("A retrieval branch returned invalid identities.")
    if (
        isinstance(chunk_index, bool)
        or not isinstance(chunk_index, int)
        or chunk_index < 0
    ):
        raise HybridResultError("A retrieval branch returned an invalid index.")
    if not isinstance(content, str) or not content.strip():
        raise HybridResultError("A retrieval branch returned invalid content.")
    if isinstance(page, bool) or not isinstance(page, int) or page < 1:
        raise HybridResultError("A retrieval branch returned an invalid page.")
    if not isinstance(filename, str) or not filename.strip():
        raise HybridResultError("A retrieval branch returned an invalid filename.")
    validated_metadata = _validated_metadata(metadata)
    return _RankedPayload(
        chunk_id=chunk_id,
        doc_id=doc_id,
        chunk_index=chunk_index,
        content=content,
        page=page,
        filename=filename,
        metadata=validated_metadata,
        rank=rank,
    )


def _validated_metadata(value: Any) -> dict[str, JSONScalar]:
    if not isinstance(value, dict):
        raise HybridResultError("A retrieval branch returned invalid metadata.")
    validated: dict[str, JSONScalar] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise HybridResultError("A retrieval branch returned invalid metadata.")
        if item is None or isinstance(item, (str, bool, int)):
            validated[key] = item
            continue
        if isinstance(item, float) and math.isfinite(item):
            validated[key] = item
            continue
        raise HybridResultError("A retrieval branch returned invalid metadata.")
    return validated


def _same_payload(first: _RankedPayload, second: _RankedPayload) -> bool:
    return (
        first.chunk_id == second.chunk_id
        and first.doc_id == second.doc_id
        and first.chunk_index == second.chunk_index
        and first.content == second.content
        and first.page == second.page
        and first.filename == second.filename
        and first.metadata.keys() == second.metadata.keys()
        and all(
            type(value) is type(second.metadata[key])
            and value == second.metadata[key]
            for key, value in first.metadata.items()
        )
    )


def _best_rank(item: HybridRetrievedChunk) -> int:
    ranks = [
        rank
        for rank in (item.vector_rank, item.bm25_rank)
        if rank is not None
    ]
    if not ranks:  # pragma: no cover - every fused item came from a branch
        raise HybridError("The Hybrid fusion ranks are invalid.")
    return min(ranks)


def _validated_top_k(top_k: int) -> int:
    if isinstance(top_k, bool) or not isinstance(top_k, int):
        raise ValueError("top_k must be an integer")
    if not RETRIEVAL_TOP_K_MIN <= top_k <= RETRIEVAL_TOP_K_MAX:
        raise ValueError(
            f"top_k must be between {RETRIEVAL_TOP_K_MIN} and "
            f"{RETRIEVAL_TOP_K_MAX}"
        )
    return top_k


def _validated_rank_constant(rank_constant: int) -> int:
    if (
        isinstance(rank_constant, bool)
        or not isinstance(rank_constant, int)
        or rank_constant <= 0
    ):
        raise ValueError("rank_constant must be a positive integer")
    return rank_constant


def _log_search_event(
    *,
    query: str,
    top_k: int,
    doc_id: UUID | None,
    vector_result_count: int,
    bm25_result_count: int,
    results: Sequence[HybridRetrievedChunk],
) -> None:
    event = {
        "event": HYBRID_SEARCH_EVENT,
        "query_sha256": hashlib.sha256(query.encode("utf-8")).hexdigest(),
        "query_len": len(query),
        "top_k": top_k,
        "candidate_k": HYBRID_CANDIDATE_K,
        "rrf_rank_constant": RRF_RANK_CONSTANT,
        "filter_doc_id": None if doc_id is None else str(doc_id),
        "vector_result_count": vector_result_count,
        "bm25_result_count": bm25_result_count,
        "result_count": len(results),
        "results": [
            {
                "rank": rank,
                "chunk_id": str(result.chunk_id),
                "doc_id": str(result.doc_id),
                "vector_rank": result.vector_rank,
                "bm25_rank": result.bm25_rank,
                "rrf_score": result.score,
            }
            for rank, result in enumerate(results, start=1)
        ],
    }
    try:
        message = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError):
        logger.error("Hybrid search event serialization failed.")
        return
    logger.bind(**{JSONL_LOG_MARKER: True}).info(message)


@lru_cache
def get_hybrid_retrieval_service() -> HybridRetrievalService:
    """Return the lazy process-wide Hybrid orchestration service."""
    return HybridRetrievalService(get_retrieval_service(), get_bm25_service())
