"""Opt-in real vector, BM25, and Hybrid comparison on identical Chunks."""

from __future__ import annotations

import json
import os
import unicodedata
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import asdict, dataclass, replace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from qdrant_client import QdrantClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from backend.app.api.hybrid import require_hybrid_retrieval_service
from backend.app.core.config import EmbeddingSettings, PROJECT_ROOT, QdrantSettings
from backend.app.core.database import get_session_factory
from backend.app.main import create_app
from backend.app.models.chunk import Chunk
from backend.app.models.document import Document
from backend.app.services.bm25 import BM25Service, load_bm25_chunks
from backend.app.services.document_parser import PageText
from backend.app.services.embedding import EmbeddingClient
from backend.app.services.hybrid import (
    HYBRID_CANDIDATE_K,
    HybridRetrievalService,
    reciprocal_rank_fusion,
)
from backend.app.services.qdrant_store import QdrantVectorStore, VectorizedChunk
from backend.app.services.retrieval import RetrievalService
from backend.app.services.text_splitter import ChunkDraft, split_pages
from backend.tests.day10_bm25_cases import COMPARISON_CASES, NEGATIVE_QUESTIONS
from backend.tests.day9_tuning_corpus import page_texts

EVALUATION_K = 5
EXPECTED_POSITIVE_METRICS: dict[str, object] = {
    "overall": {
        "vector": {"hit_at_1": 0.75, "hit_at_5": 0.917, "mrr_at_5": 0.812},
        "bm25": {"hit_at_1": 0.833, "hit_at_5": 1.0, "mrr_at_5": 0.882},
        "hybrid": {"hit_at_1": 0.917, "hit_at_5": 1.0, "mrr_at_5": 0.944},
    },
    "by_category": {
        "exact_identifier": {
            "vector": {"hit_at_1": 0.75, "hit_at_5": 1.0, "mrr_at_5": 0.812},
            "bm25": {"hit_at_1": 1.0, "hit_at_5": 1.0, "mrr_at_5": 1.0},
            "hybrid": {"hit_at_1": 1.0, "hit_at_5": 1.0, "mrr_at_5": 1.0},
        },
        "semantic_paraphrase": {
            "vector": {"hit_at_1": 0.5, "hit_at_5": 0.75, "mrr_at_5": 0.625},
            "bm25": {"hit_at_1": 0.5, "hit_at_5": 1.0, "mrr_at_5": 0.646},
            "hybrid": {"hit_at_1": 0.75, "hit_at_5": 1.0, "mrr_at_5": 0.833},
        },
        "mixed": {
            "vector": {"hit_at_1": 1.0, "hit_at_5": 1.0, "mrr_at_5": 1.0},
            "bm25": {"hit_at_1": 1.0, "hit_at_5": 1.0, "mrr_at_5": 1.0},
            "hybrid": {"hit_at_1": 1.0, "hit_at_5": 1.0, "mrr_at_5": 1.0},
        },
    },
}
EXPECTED_NEGATIVE_RETURN_RATE = {
    "vector": 1.0,
    "bm25": 0.0,
    "hybrid": 1.0,
}
QueryIdentity = tuple[str, str, str]
EXPECTED_QUERY_IDENTITIES: tuple[QueryIdentity, ...] = (
    ("exact_identifier", "6203", "服务分机是 6203"),
    ("exact_identifier", "五万元采购", "总经理审批"),
    ("exact_identifier", "网络组", "服务分机是 6203"),
    ("exact_identifier", "全量备份", "每周日凌晨两点"),
    (
        "semantic_paraphrase",
        "远程接入工具坏了应该找谁处理？",
        "服务分机是 6203",
    ),
    (
        "semantic_paraphrase",
        "新人多久能拿到办公设备？",
        "三个工作日内发放",
    ),
    (
        "semantic_paraphrase",
        "差旅单据交财务的截止日是什么时候？",
        "每月二十五日前",
    ),
    (
        "semantic_paraphrase",
        "周末什么时候做整库备份？",
        "每周日凌晨两点",
    ),
    ("mixed", "VPN 出错后拨打哪个 6203 服务？", "服务分机是 6203"),
    ("mixed", "采购超过五万元要找最高负责人审批吗？", "总经理审批"),
    ("mixed", "访客登记后如何进入办公区？", "访客登记"),
    ("mixed", "会议室最多能占用多久？", "最长不得超过两个小时"),
)
QueryDetail = tuple[
    int | None,
    int | None,
    int | None,
    int | None,
    int | None,
    float,
    int,
    int,
]
EXPECTED_QUERY_DETAILS: tuple[QueryDetail, ...] = (
    (4, 1, 1, 4, 1, 0.050, 19, 0),
    (1, 1, 1, 1, 1, 0.450, 11, 0),
    (1, 1, 1, 1, 1, 0.150, 17, 0),
    (1, 1, 1, 1, 1, 0.500, 10, 0),
    (None, 3, 3, 7, 3, 0.739, 3, 3),
    (1, 4, 1, 1, 4, 0.739, 3, 3),
    (2, 1, 1, 2, 1, 0.667, 4, 4),
    (1, 1, 1, 1, 1, 0.727, 4, 2),
    (1, 1, 1, 1, 1, 0.667, 4, 4),
    (1, 1, 1, 1, 1, 0.739, 3, 3),
    (1, 1, 1, 1, 1, 0.739, 3, 3),
    (1, 1, 1, 1, 1, 0.636, 6, 2),
)
EXPECTED_CANDIDATE_STATISTICS: dict[str, object] = {
    "mean_candidate_overlap_rate": 0.567,
    "branch_unique_candidate_hits": {"vector_only": 0, "bm25_only": 0},
    "branch_unique_candidate_counts": {"vector_only": 87, "bm25_only": 24},
    "hybrid_recovered_top5_misses": {"vector": 1, "bm25": 0},
}

requires_real_stack = pytest.mark.skipif(
    any(
        os.environ.get(flag) != "1"
        for flag in (
            "RUN_POSTGRES_INTEGRATION",
            "RUN_QDRANT_INTEGRATION",
            "RUN_LOCAL_EMBEDDING_INTEGRATION",
        )
    ),
    reason="enable real PostgreSQL, local BGE, and Qdrant integration",
)


@dataclass(frozen=True, slots=True)
class ThreeWayComparison:
    """Objective Top-5 ranks from all three retrieval methods."""

    category: str
    question: str
    expected_phrase: str
    vector_rank: int | None
    bm25_rank: int | None
    hybrid_rank: int | None
    vector_candidate_rank: int | None
    bm25_candidate_rank: int | None
    candidate_overlap_rate: float
    vector_only_candidate_count: int
    bm25_only_candidate_count: int


def _baseline_comparisons() -> list[ThreeWayComparison]:
    """Build the committed per-query baseline without external services."""
    return [
        ThreeWayComparison(
            category=case["category"],
            question=case["question"],
            expected_phrase=case["expected_phrase"],
            vector_rank=details[0],
            bm25_rank=details[1],
            hybrid_rank=details[2],
            vector_candidate_rank=details[3],
            bm25_candidate_rank=details[4],
            candidate_overlap_rate=details[5],
            vector_only_candidate_count=details[6],
            bm25_only_candidate_count=details[7],
        )
        for case, details in zip(
            COMPARISON_CASES,
            EXPECTED_QUERY_DETAILS,
            strict=True,
        )
    ]


def _assert_experiment_acceptance(
    comparisons: Sequence[ThreeWayComparison],
    negative_return_rate: dict[str, float],
) -> None:
    """Apply the committed Day 11 experiment acceptance contract."""
    assert _query_identities(comparisons) == EXPECTED_QUERY_IDENTITIES
    assert _positive_metrics(comparisons) == EXPECTED_POSITIVE_METRICS
    assert _query_details(comparisons) == EXPECTED_QUERY_DETAILS
    assert _candidate_statistics(comparisons) == EXPECTED_CANDIDATE_STATISTICS
    assert negative_return_rate == EXPECTED_NEGATIVE_RETURN_RATE


def test_experiment_acceptance_rejects_candidate_detail_drift() -> None:
    """Candidate-set drift must fail even when aggregate ranks are unchanged."""
    comparisons = _baseline_comparisons()
    comparisons[0] = replace(
        comparisons[0],
        candidate_overlap_rate=0.0,
        vector_only_candidate_count=20,
        bm25_only_candidate_count=1,
    )

    with pytest.raises(AssertionError):
        _assert_experiment_acceptance(
            comparisons,
            EXPECTED_NEGATIVE_RETURN_RATE,
        )


def test_experiment_acceptance_rejects_query_identity_order_drift() -> None:
    """Query identity order must stay fixed when numeric details are identical."""
    comparisons = _baseline_comparisons()
    comparisons[9], comparisons[10] = comparisons[10], comparisons[9]

    with pytest.raises(AssertionError):
        _assert_experiment_acceptance(
            comparisons,
            EXPECTED_NEGATIVE_RETURN_RATE,
        )


def normalized(text: str) -> str:
    """Use the committed Day 9 NFKC plus strip hit rule."""
    return unicodedata.normalize("NFKC", text).strip()


def hit_rank(results: Sequence[object], expected_phrase: str) -> int | None:
    """Return the first result rank containing the fixed expected phrase."""
    expected = normalized(expected_phrase)
    return next(
        (
            rank
            for rank, result in enumerate(results, start=1)
            if expected in normalized(getattr(result, "content"))
        ),
        None,
    )


def aggregate(ranks: Sequence[int | None]) -> dict[str, float]:
    """Calculate objective Top-5 ranking metrics."""
    count = len(ranks)
    return {
        "hit_at_1": round(sum(rank == 1 for rank in ranks) / count, 3),
        "hit_at_5": round(sum(rank is not None for rank in ranks) / count, 3),
        "mrr_at_5": round(
            sum(1 / rank for rank in ranks if rank is not None) / count,
            3,
        ),
    }


@pytest.mark.integration
@requires_real_stack
def test_real_vector_bm25_and_hybrid_on_identical_chunks() -> None:
    """Measure three rankers on one corpus and always remove both fixtures."""
    pages = [
        PageText(page=index, text=text)
        for index, text in enumerate(page_texts(), start=1)
    ]
    drafts = split_pages(
        pages,
        chunk_size=500,
        chunk_overlap=100,
        encoding_name="o200k_base",
    )
    assert len(drafts) == 24
    document_id = uuid4()
    chunk_ids = [uuid4() for _ in drafts]
    filename = "day11-hybrid-comparison-handbook.txt"
    factory = get_session_factory()
    collection = f"day11_hybrid_compare_{uuid4().hex}"
    qdrant_settings = QdrantSettings(
        _env_file=None,
        host="127.0.0.1",
        port=6333,
        collection=collection,
    )
    qdrant_client = QdrantClient(
        url=qdrant_settings.build_url(),
        timeout=qdrant_settings.timeout_seconds,
        prefer_grpc=False,
    )
    vector_store = QdrantVectorStore(qdrant_settings, client=qdrant_client)
    embedding_client = EmbeddingClient(
        EmbeddingSettings(
            _env_file=None,
            cache_dir=PROJECT_ROOT / "data" / "models",
        )
    )
    try:
        _insert_corpus(
            factory=factory,
            document_id=document_id,
            chunk_ids=chunk_ids,
            filename=filename,
            drafts=drafts,
        )
        postgres_chunks = tuple(
            chunk
            for chunk in load_bm25_chunks(session_factory=factory)
            if chunk.doc_id == document_id
        )
        assert {chunk.chunk_id for chunk in postgres_chunks} == set(chunk_ids)
        bm25_service = BM25Service(lambda: postgres_chunks)

        vectors = embedding_client.embed_documents(
            [chunk.content for chunk in postgres_chunks]
        )
        vectorized = [
            VectorizedChunk(
                chunk_id=chunk.chunk_id,
                doc_id=chunk.doc_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                page=chunk.page,
                filename=chunk.filename,
                metadata=dict(chunk.metadata),
                vector=vector,
            )
            for chunk, vector in zip(postgres_chunks, vectors, strict=True)
        ]
        vector_store.initialize_collection()
        assert vector_store.upsert_chunks(vectorized) == len(vectorized)

        application = create_app()
        hybrid_service = HybridRetrievalService(
            RetrievalService(embedding_client, vector_store),
            bm25_service,
        )
        application.dependency_overrides[require_hybrid_retrieval_service] = (
            lambda: hybrid_service
        )
        with TestClient(application) as client:
            response = client.post(
                "/retrieval/hybrid/search",
                json={"query": "6203", "top_k": 1, "doc_id": str(document_id)},
            )
            assert response.status_code == 200
            result = response.json()["results"]
            assert len(result) == 1
            assert result[0]["doc_id"] == str(document_id)
            assert "服务分机是 6203" in result[0]["content"]
            assert 0 < result[0]["score"] <= 2 / 61
            assert "vector_rank" not in result[0]
            assert "bm25_rank" not in result[0]
            missing = client.post(
                "/retrieval/hybrid/search",
                json={"query": "6203", "doc_id": str(uuid4())},
            )
            assert missing.status_code == 200
            assert missing.json() == {"results": []}

        comparisons: list[ThreeWayComparison] = []
        for case in COMPARISON_CASES:
            vector_candidates = vector_store.search(
                embedding_client.embed_query(case["question"]),
                limit=HYBRID_CANDIDATE_K,
            )
            bm25_candidates = bm25_service.search(
                case["question"],
                top_k=HYBRID_CANDIDATE_K,
            )
            hybrid_results = reciprocal_rank_fusion(
                vector_candidates,
                bm25_candidates,
                top_k=EVALUATION_K,
            )
            vector_ids = {result.chunk_id for result in vector_candidates}
            bm25_ids = {result.chunk_id for result in bm25_candidates}
            union_ids = vector_ids | bm25_ids
            comparisons.append(
                ThreeWayComparison(
                    category=case["category"],
                    question=case["question"],
                    expected_phrase=case["expected_phrase"],
                    vector_rank=hit_rank(
                        vector_candidates[:EVALUATION_K],
                        case["expected_phrase"],
                    ),
                    bm25_rank=hit_rank(
                        bm25_candidates[:EVALUATION_K],
                        case["expected_phrase"],
                    ),
                    hybrid_rank=hit_rank(
                        hybrid_results,
                        case["expected_phrase"],
                    ),
                    vector_candidate_rank=hit_rank(
                        vector_candidates,
                        case["expected_phrase"],
                    ),
                    bm25_candidate_rank=hit_rank(
                        bm25_candidates,
                        case["expected_phrase"],
                    ),
                    candidate_overlap_rate=round(
                        len(vector_ids & bm25_ids) / len(union_ids),
                        3,
                    )
                    if union_ids
                    else 1.0,
                    vector_only_candidate_count=len(vector_ids - bm25_ids),
                    bm25_only_candidate_count=len(bm25_ids - vector_ids),
                )
            )

        negative_returns = {"vector": 0, "bm25": 0, "hybrid": 0}
        for question in NEGATIVE_QUESTIONS:
            vector_candidates = vector_store.search(
                embedding_client.embed_query(question),
                limit=HYBRID_CANDIDATE_K,
            )
            bm25_candidates = bm25_service.search(
                question,
                top_k=HYBRID_CANDIDATE_K,
            )
            hybrid_results = reciprocal_rank_fusion(
                vector_candidates,
                bm25_candidates,
                top_k=EVALUATION_K,
            )
            negative_returns["vector"] += bool(vector_candidates[:EVALUATION_K])
            negative_returns["bm25"] += bool(bm25_candidates[:EVALUATION_K])
            negative_returns["hybrid"] += bool(hybrid_results)

        positive_metrics = _positive_metrics(comparisons)
        candidate_statistics = _candidate_statistics(comparisons)
        summary = {
            "experiment": "day11_vector_bm25_hybrid",
            "chunk_size": 500,
            "chunk_overlap": 100,
            "candidate_k": HYBRID_CANDIDATE_K,
            "evaluation_k": EVALUATION_K,
            "rrf_rank_constant": 60,
            "corpus_chunk_count": len(postgres_chunks),
            "positive_question_count": len(comparisons),
            "negative_question_count": len(NEGATIVE_QUESTIONS),
            **positive_metrics,
            "negative_return_rate": {
                method: round(count / len(NEGATIVE_QUESTIONS), 3)
                for method, count in negative_returns.items()
            },
            **candidate_statistics,
            "queries": [asdict(comparison) for comparison in comparisons],
        }
        print("\nDAY11_HYBRID_COMPARISON_RESULT " + json.dumps(summary, ensure_ascii=False))

        _assert_experiment_acceptance(
            comparisons,
            summary["negative_return_rate"],
        )
    finally:
        try:
            try:
                if qdrant_client.collection_exists(collection):
                    qdrant_client.delete_collection(collection_name=collection)
                    assert not qdrant_client.collection_exists(collection)
            finally:
                qdrant_client.close()
        finally:
            _delete_document(factory, document_id)


def _positive_metrics(
    comparisons: Sequence[ThreeWayComparison],
) -> dict[str, object]:
    by_category: dict[str, list[ThreeWayComparison]] = defaultdict(list)
    for comparison in comparisons:
        by_category[comparison.category].append(comparison)
    methods = ("vector", "bm25", "hybrid")
    return {
        "overall": {
            method: aggregate(
                [getattr(item, f"{method}_rank") for item in comparisons]
            )
            for method in methods
        },
        "by_category": {
            category: {
                method: aggregate(
                    [getattr(item, f"{method}_rank") for item in items]
                )
                for method in methods
            }
            for category, items in sorted(by_category.items())
        },
    }


def _query_details(
    comparisons: Sequence[ThreeWayComparison],
) -> tuple[QueryDetail, ...]:
    """Project every documented per-query rank and candidate statistic."""
    return tuple(
        (
            item.vector_rank,
            item.bm25_rank,
            item.hybrid_rank,
            item.vector_candidate_rank,
            item.bm25_candidate_rank,
            item.candidate_overlap_rate,
            item.vector_only_candidate_count,
            item.bm25_only_candidate_count,
        )
        for item in comparisons
    )


def _query_identities(
    comparisons: Sequence[ThreeWayComparison],
) -> tuple[QueryIdentity, ...]:
    """Project the documented query identities in their committed order."""
    return tuple(
        (item.category, item.question, item.expected_phrase)
        for item in comparisons
    )


def _candidate_statistics(
    comparisons: Sequence[ThreeWayComparison],
) -> dict[str, object]:
    """Calculate the candidate-level statistics published in the report."""
    return {
        "mean_candidate_overlap_rate": round(
            sum(item.candidate_overlap_rate for item in comparisons)
            / len(comparisons),
            3,
        ),
        "branch_unique_candidate_hits": {
            "vector_only": sum(
                item.vector_candidate_rank is not None
                and item.bm25_candidate_rank is None
                for item in comparisons
            ),
            "bm25_only": sum(
                item.bm25_candidate_rank is not None
                and item.vector_candidate_rank is None
                for item in comparisons
            ),
        },
        "branch_unique_candidate_counts": {
            "vector_only": sum(
                item.vector_only_candidate_count for item in comparisons
            ),
            "bm25_only": sum(
                item.bm25_only_candidate_count for item in comparisons
            ),
        },
        "hybrid_recovered_top5_misses": {
            "vector": sum(
                item.vector_rank is None and item.hybrid_rank is not None
                for item in comparisons
            ),
            "bm25": sum(
                item.bm25_rank is None and item.hybrid_rank is not None
                for item in comparisons
            ),
        },
    }


def _insert_corpus(
    *,
    factory: sessionmaker[Session],
    document_id: UUID,
    chunk_ids: list[UUID],
    filename: str,
    drafts: list[ChunkDraft],
) -> None:
    """Persist the exact comparison corpus in PostgreSQL."""
    extracted_text = "\f".join(page_texts())
    with factory() as session:
        session.add(
            Document(
                id=document_id,
                filename=filename,
                size=len(extracted_text.encode("utf-8")),
                status="ready",
                extracted_text=extracted_text,
            )
        )
        session.flush()
        session.add_all(
            [
                Chunk(
                    chunk_id=chunk_id,
                    doc_id=document_id,
                    chunk_index=draft.chunk_index,
                    content=draft.content,
                    page=draft.page,
                    chunk_metadata=dict(draft.metadata),
                )
                for chunk_id, draft in zip(chunk_ids, drafts, strict=True)
            ]
        )
        session.commit()


def _delete_document(
    factory: sessionmaker[Session],
    document_id: UUID,
) -> None:
    """Delete the PostgreSQL fixture and verify cascade cleanup."""
    with factory() as session:
        document = session.get(Document, document_id)
        if document is not None:
            session.delete(document)
            session.commit()
        assert session.scalars(
            select(Chunk).where(Chunk.doc_id == document_id)
        ).all() == []
