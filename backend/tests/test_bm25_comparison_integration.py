"""Opt-in real vector-versus-BM25 comparison on one shared Chunk corpus."""

from __future__ import annotations

import json
import os
import unicodedata
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from typing import cast
from uuid import UUID, uuid4

import pytest
from qdrant_client import QdrantClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import EmbeddingSettings, PROJECT_ROOT, QdrantSettings
from backend.app.core.database import get_session_factory
from backend.app.models.chunk import Chunk
from backend.app.models.document import Document
from backend.app.services.bm25 import BM25CorpusChunk, BM25Service, load_bm25_chunks
from backend.app.services.document_parser import PageText
from backend.app.services.embedding import EmbeddingClient
from backend.app.services.qdrant_store import QdrantVectorStore, VectorizedChunk
from backend.app.services.text_splitter import ChunkDraft, split_pages
from backend.tests.day10_bm25_cases import COMPARISON_CASES, NEGATIVE_QUESTIONS
from backend.tests.day9_tuning_corpus import page_texts

TOP_K = 5
EXPECTED_POSITIVE_METRICS: dict[str, object] = {
    "overall": {
        "vector": {"hit_at_1": 0.75, "hit_at_5": 0.917, "mrr_at_5": 0.812},
        "bm25": {"hit_at_1": 0.833, "hit_at_5": 1.0, "mrr_at_5": 0.882},
    },
    "by_category": {
        "exact_identifier": {
            "vector": {"hit_at_1": 0.75, "hit_at_5": 1.0, "mrr_at_5": 0.812},
            "bm25": {"hit_at_1": 1.0, "hit_at_5": 1.0, "mrr_at_5": 1.0},
        },
        "semantic_paraphrase": {
            "vector": {"hit_at_1": 0.5, "hit_at_5": 0.75, "mrr_at_5": 0.625},
            "bm25": {"hit_at_1": 0.5, "hit_at_5": 1.0, "mrr_at_5": 0.646},
        },
        "mixed": {
            "vector": {"hit_at_1": 1.0, "hit_at_5": 1.0, "mrr_at_5": 1.0},
            "bm25": {"hit_at_1": 1.0, "hit_at_5": 1.0, "mrr_at_5": 1.0},
        },
    },
}
EXPECTED_NEGATIVE_RETURN_RATE = {"vector": 1.0, "bm25": 0.0}

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
class QueryComparison:
    """One objective pair of ranks for the same expected phrase."""

    category: str
    question: str
    expected_phrase: str
    vector_rank: int | None
    bm25_rank: int | None


def normalized(text: str) -> str:
    """Use the Day 9 objective phrase normalization."""
    return unicodedata.normalize("NFKC", text).strip()


def hit_rank(results: list[object], expected_phrase: str) -> int | None:
    """Return the first rank containing the fixed expected phrase."""
    expected = normalized(expected_phrase)
    return next(
        (
            rank
            for rank, result in enumerate(results, start=1)
            if expected in normalized(getattr(result, "content"))
        ),
        None,
    )


def aggregate(ranks: list[int | None]) -> dict[str, float]:
    """Calculate rank metrics without comparing raw retrieval scores."""
    count = len(ranks)
    return {
        "hit_at_1": round(sum(rank == 1 for rank in ranks) / count, 3),
        "hit_at_5": round(sum(rank is not None for rank in ranks) / count, 3),
        "mrr_at_5": round(
            sum(1 / rank for rank in ranks if rank is not None) / count,
            3,
        ),
    }


def _assert_comparison_acceptance(
    comparisons: Sequence[QueryComparison],
    *,
    vector_negative_returns: int,
    bm25_negative_returns: int,
) -> None:
    """Require the fixed corpus to reproduce its committed retrieval metrics."""
    by_category: dict[str, list[QueryComparison]] = defaultdict(list)
    for comparison in comparisons:
        by_category[comparison.category].append(comparison)
    positive_metrics = {
        "overall": {
            "vector": aggregate([item.vector_rank for item in comparisons]),
            "bm25": aggregate([item.bm25_rank for item in comparisons]),
        },
        "by_category": {
            category: {
                "vector": aggregate([item.vector_rank for item in items]),
                "bm25": aggregate([item.bm25_rank for item in items]),
            }
            for category, items in sorted(by_category.items())
        },
    }
    negative_return_rate = {
        "vector": round(vector_negative_returns / len(NEGATIVE_QUESTIONS), 3),
        "bm25": round(bm25_negative_returns / len(NEGATIVE_QUESTIONS), 3),
    }

    assert positive_metrics == EXPECTED_POSITIVE_METRICS
    assert negative_return_rate == EXPECTED_NEGATIVE_RETURN_RATE


def _cleanup_comparison_resources(
    *,
    qdrant_client: QdrantClient,
    collection: str,
    factory: sessionmaker[Session],
    document_id: UUID,
    delete_document: Callable[[sessionmaker[Session], UUID], None],
) -> None:
    """Remove the temporary Qdrant collection and PostgreSQL fixture."""
    try:
        try:
            if qdrant_client.collection_exists(collection):
                qdrant_client.delete_collection(collection_name=collection)
        finally:
            qdrant_client.close()
    finally:
        delete_document(factory, document_id)


def test_comparison_acceptance_rejects_all_positive_misses() -> None:
    """An experiment with no positive Top-5 hits must fail acceptance."""
    comparisons = [
        QueryComparison(
            category=case["category"],
            question=case["question"],
            expected_phrase=case["expected_phrase"],
            vector_rank=None,
            bm25_rank=None,
        )
        for case in COMPARISON_CASES
    ]

    with pytest.raises(AssertionError):
        _assert_comparison_acceptance(
            comparisons,
            vector_negative_returns=len(NEGATIVE_QUESTIONS),
            bm25_negative_returns=0,
        )


class FailingQdrantCleanupClient:
    """Fail collection deletion while recording whether close still ran."""

    def __init__(self) -> None:
        self.closed = False

    def collection_exists(self, _: str) -> bool:
        return True

    def delete_collection(self, *, collection_name: str) -> None:
        raise RuntimeError(f"cannot delete {collection_name}")

    def close(self) -> None:
        self.closed = True


def test_qdrant_cleanup_failure_still_deletes_postgres_document() -> None:
    """PostgreSQL cleanup must not depend on Qdrant cleanup succeeding."""
    client = FailingQdrantCleanupClient()
    factory = cast(sessionmaker[Session], object())
    document_id = uuid4()
    deleted: list[tuple[sessionmaker[Session], UUID]] = []

    with pytest.raises(RuntimeError, match="cannot delete temporary_collection"):
        _cleanup_comparison_resources(
            qdrant_client=cast(QdrantClient, client),
            collection="temporary_collection",
            factory=factory,
            document_id=document_id,
            delete_document=lambda received_factory, received_id: deleted.append(
                (received_factory, received_id)
            ),
        )

    assert client.closed is True
    assert deleted == [(factory, document_id)]


@pytest.mark.integration
@requires_real_stack
def test_real_vector_vs_bm25_on_identical_chunks() -> None:
    """Generate per-query and aggregate metrics, then clean both stores."""
    assert len(COMPARISON_CASES) >= 12
    assert {case["category"] for case in COMPARISON_CASES} == {
        "exact_identifier",
        "semantic_paraphrase",
        "mixed",
    }

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
    document_id = uuid4()
    chunk_ids = [uuid4() for _ in drafts]
    filename = "day10-comparison-handbook.txt"
    factory = get_session_factory()
    collection = f"day10_compare_{uuid4().hex}"
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
        assert {chunk.chunk_id for chunk in vectorized} == {
            chunk.chunk_id for chunk in postgres_chunks
        }
        vector_store.initialize_collection()
        assert vector_store.upsert_chunks(vectorized) == len(vectorized)

        comparisons: list[QueryComparison] = []
        for case in COMPARISON_CASES:
            vector_results = vector_store.search(
                embedding_client.embed_query(case["question"]),
                limit=TOP_K,
            )
            bm25_results = bm25_service.search(case["question"], top_k=TOP_K)
            comparisons.append(
                QueryComparison(
                    category=case["category"],
                    question=case["question"],
                    expected_phrase=case["expected_phrase"],
                    vector_rank=hit_rank(vector_results, case["expected_phrase"]),
                    bm25_rank=hit_rank(bm25_results, case["expected_phrase"]),
                )
            )

        by_category: dict[str, list[QueryComparison]] = defaultdict(list)
        for comparison in comparisons:
            by_category[comparison.category].append(comparison)
        category_metrics = {
            category: {
                "vector": aggregate([item.vector_rank for item in items]),
                "bm25": aggregate([item.bm25_rank for item in items]),
            }
            for category, items in sorted(by_category.items())
        }
        vector_negative_returns = 0
        bm25_negative_returns = 0
        for question in NEGATIVE_QUESTIONS:
            vector_negative_returns += bool(
                vector_store.search(
                    embedding_client.embed_query(question),
                    limit=TOP_K,
                )
            )
            bm25_negative_returns += bool(
                bm25_service.search(question, top_k=TOP_K)
            )

        summary = {
            "experiment": "day10_vector_vs_bm25",
            "chunk_size": 500,
            "chunk_overlap": 100,
            "top_k": TOP_K,
            "corpus_chunk_count": len(postgres_chunks),
            "positive_question_count": len(comparisons),
            "negative_question_count": len(NEGATIVE_QUESTIONS),
            "overall": {
                "vector": aggregate([item.vector_rank for item in comparisons]),
                "bm25": aggregate([item.bm25_rank for item in comparisons]),
            },
            "by_category": category_metrics,
            "negative_return_rate": {
                "vector": round(
                    vector_negative_returns / len(NEGATIVE_QUESTIONS), 3
                ),
                "bm25": round(
                    bm25_negative_returns / len(NEGATIVE_QUESTIONS), 3
                ),
            },
            "queries": [asdict(comparison) for comparison in comparisons],
        }
        print("\nDAY10_COMPARISON_RESULT " + json.dumps(summary, ensure_ascii=False))

        assert len(comparisons) == len(COMPARISON_CASES)
        _assert_comparison_acceptance(
            comparisons,
            vector_negative_returns=vector_negative_returns,
            bm25_negative_returns=bm25_negative_returns,
        )
    finally:
        _cleanup_comparison_resources(
            qdrant_client=qdrant_client,
            collection=collection,
            factory=factory,
            document_id=document_id,
            delete_document=_delete_document,
        )


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
    """Remove the real PostgreSQL fixture and verify Chunk cascade cleanup."""
    with factory() as session:
        document = session.get(Document, document_id)
        if document is not None:
            session.delete(document)
            session.commit()
        assert session.scalars(
            select(Chunk).where(Chunk.doc_id == document_id)
        ).all() == []
