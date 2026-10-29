"""Day 11 corpus, real Hybrid vs pinned Rerank, and RAG refusal acceptance."""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from qdrant_client import QdrantClient

from backend.app.api.chat import require_rag_service
from backend.app.api.rerank import require_reranked_retrieval_service
from backend.app.core.config import EmbeddingSettings, QdrantSettings, RAGSettings, RerankerSettings
from backend.app.core.database import get_session_factory
from backend.app.main import create_app
from backend.app.services.bm25 import BM25Service, load_bm25_chunks
from backend.app.services.document_parser import PageText
from backend.app.services.embedding import EmbeddingClient
from backend.app.services.hybrid import HybridRetrievalService
from backend.app.services.qdrant_store import QdrantVectorStore, VectorizedChunk
from backend.app.services.rag import NO_RELEVANT_KNOWLEDGE, RAGService
from backend.app.services.reranker import RerankedRetrievalService, RerankerService
from backend.app.services.retrieval import RetrievalService
from backend.app.services.text_splitter import split_pages
from backend.tests.day10_bm25_cases import COMPARISON_CASES, NEGATIVE_QUESTIONS
from backend.tests.day9_tuning_corpus import page_texts
from backend.tests.test_hybrid_comparison_integration import (
    EXPECTED_QUERY_IDENTITIES, _delete_document, _insert_corpus, aggregate, hit_rank,
)
from backend.tests.test_rag_integration import StubMessagesLLMClient

requires_real_stack = pytest.mark.skipif(
    any(os.environ.get(flag) != "1" for flag in (
        "RUN_POSTGRES_INTEGRATION", "RUN_QDRANT_INTEGRATION",
        "RUN_LOCAL_EMBEDDING_INTEGRATION", "RUN_RERANKER_INTEGRATION",
    )), reason="enable real PostgreSQL, Qdrant, local BGE and reranker",
)

EXPECTED_HYBRID_METRICS = {
    "hit_at_1": 0.917,
    "hit_at_5": 1.0,
    "mrr_at_5": 0.944,
}
EXPECTED_RERANK_METRICS = {
    "hit_at_1": 0.917,
    "hit_at_5": 1.0,
    "mrr_at_5": 0.958,
}
EXPECTED_HYBRID_RANKS = (1, 1, 1, 1, 3, 1, 1, 1, 1, 1, 1, 1)
EXPECTED_RERANK_RANKS = (1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1)


def _assert_quality_acceptance(rows: Sequence[dict[str, Any]]) -> None:
    """Apply the committed Day 12 quality acceptance contract."""
    hybrid = aggregate([row["hybrid_rank"] for row in rows])
    rerank = aggregate([row["rerank_rank"] for row in rows])
    assert hybrid == EXPECTED_HYBRID_METRICS
    assert rerank == EXPECTED_RERANK_METRICS
    assert tuple(row["hybrid_rank"] for row in rows) == EXPECTED_HYBRID_RANKS
    assert tuple(row["rerank_rank"] for row in rows) == EXPECTED_RERANK_RANKS
    assert tuple(row["candidate_count"] for row in rows) == (20,) * 12
    assert tuple(row["truncated_candidate_count"] for row in rows) == (0,) * 12


def test_quality_acceptance_rejects_all_correct_results_falling_to_fifth() -> None:
    """Stable Hit@5 cannot hide a severe Hit@1 and MRR regression."""
    rows = [
        {
            "hybrid_rank": hybrid_rank,
            "rerank_rank": 5,
            "candidate_count": 20,
            "truncated_candidate_count": 0,
        }
        for hybrid_rank in EXPECTED_HYBRID_RANKS
    ]

    assert aggregate([row["rerank_rank"] for row in rows]) == {
        "hit_at_1": 0.0,
        "hit_at_5": 1.0,
        "mrr_at_5": 0.2,
    }
    with pytest.raises(AssertionError):
        _assert_quality_acceptance(rows)


@pytest.mark.integration
@requires_real_stack
def test_real_hybrid_rerank_quality_and_chat_contract() -> None:
    """Publish honest measurements, fail on lost Top-5 recall, always clean up."""
    assert tuple((case["category"], case["question"], case["expected_phrase"])
                 for case in COMPARISON_CASES) == EXPECTED_QUERY_IDENTITIES
    drafts = split_pages([PageText(page=i, text=text) for i, text in enumerate(page_texts(), 1)],
                         chunk_size=500, chunk_overlap=100, encoding_name="o200k_base")
    assert len(drafts) == 24
    document_id = uuid4()
    chunk_ids = [uuid4() for _ in drafts]
    filename = "day12-rerank-comparison-handbook.txt"
    collection = f"day12_rerank_compare_{uuid4().hex}"
    factory = get_session_factory()
    settings = QdrantSettings(_env_file=None, host="127.0.0.1", port=6333, collection=collection)
    client = QdrantClient(url=settings.build_url(), prefer_grpc=False, timeout=settings.timeout_seconds)
    store = QdrantVectorStore(settings, client=client)
    embedding = EmbeddingClient(EmbeddingSettings(_env_file=None))
    reranker = RerankerService(RerankerSettings(_env_file=None))
    rows: list[dict[str, Any]] = []
    summary: dict[str, Any] = {}
    try:
        _insert_corpus(factory=factory, document_id=document_id, chunk_ids=chunk_ids,
                       filename=filename, drafts=drafts)
        chunks = tuple(item for item in load_bm25_chunks(session_factory=factory) if item.doc_id == document_id)
        assert {item.chunk_id for item in chunks} == set(chunk_ids)
        vectors = embedding.embed_documents([item.content for item in chunks])
        store.initialize_collection()
        store.upsert_chunks([VectorizedChunk(
            chunk_id=item.chunk_id, doc_id=item.doc_id, chunk_index=item.chunk_index,
            content=item.content, page=item.page, filename=item.filename,
            metadata=dict(item.metadata), vector=vector,
        ) for item, vector in zip(chunks, vectors, strict=True)])
        hybrid = HybridRetrievalService(RetrievalService(embedding, store), BM25Service(lambda: chunks))
        pipeline = RerankedRetrievalService(hybrid, reranker)
        for case in COMPARISON_CASES:
            original = hybrid.search(case["question"], top_k=20, doc_id=document_id)
            outcome = reranker.rerank(case["question"], original)
            assert len(outcome.results) == min(5, len(original))
            assert {item.chunk_id for item in outcome.results} <= {item.chunk_id for item in original}
            rows.append(dict(
                **case, hybrid_rank=hit_rank(original[:5], case["expected_phrase"]),
                rerank_rank=hit_rank(outcome.results, case["expected_phrase"]),
                candidate_count=len(original), truncated_candidate_count=outcome.truncated_candidate_count,
                model_load_seconds=outcome.model_load_seconds, inference_seconds=outcome.inference_seconds,
                top5=[dict(chunk_index=item.chunk_index, page=item.page, hybrid_rank=item.hybrid_rank,
                           rerank_rank=item.rerank_rank, rank_change=item.rank_change, score=item.score)
                      for item in outcome.results],
            ))
        warm = reranker.rerank(COMPARISON_CASES[0]["question"],
                              hybrid.search(COMPARISON_CASES[0]["question"], top_k=20, doc_id=document_id))
        llm = StubMessagesLLMClient()
        rag = RAGService(pipeline, llm, RAGSettings(_env_file=None))  # type: ignore[arg-type]
        negative_refusals = []
        for question in NEGATIVE_QUESTIONS:
            prepared = rag.prepare(question)
            answer = rag.complete(prepared)
            negative_refusals.append(answer.answer == NO_RELEVANT_KNOWLEDGE and not answer.sources)
        assert llm.calls == []
        assert all(negative_refusals)

        application = create_app()
        application.dependency_overrides[require_reranked_retrieval_service] = lambda: pipeline
        application.dependency_overrides[require_rag_service] = lambda: rag
        with TestClient(application) as api:
            response = api.post("/retrieval/rerank/search", json={"query": "6203", "doc_id": str(document_id)})
            assert response.status_code == 200
            assert len(response.json()["results"]) == 5
            assert all(item["doc_id"] == str(document_id) for item in response.json()["results"])
            missing = api.post("/retrieval/rerank/search", json={"query": "6203", "doc_id": str(uuid4())})
            assert missing.status_code == 200 and missing.json() == {"results": []}
            positive = api.post("/chat", json={"message": "VPN 故障联系谁，服务分机是多少？"})
            assert positive.status_code == 200
            assert positive.json()["sources"]
            assert all(item["filename"] == filename for item in positive.json()["sources"])
            streamed = api.post("/chat", json={"message": "VPN 故障联系谁，服务分机是多少？", "stream": True})
            assert streamed.status_code == 200
            assert streamed.text.index("event: sources") < streamed.text.index("data: [DONE]")

        summary = dict(
            experiment="day12_hybrid_vs_rerank", model_name=reranker.settings.model_name,
            revision=reranker.settings.model_revision, corpus_chunk_count=len(chunks),
            positive_question_count=len(rows), negative_question_count=len(NEGATIVE_QUESTIONS),
            hybrid=aggregate([row["hybrid_rank"] for row in rows]),
            rerank=aggregate([row["rerank_rank"] for row in rows]),
            cold_model_load_seconds=rows[0]["model_load_seconds"],
            cold_inference_seconds=rows[0]["inference_seconds"],
            warm_inference_seconds=warm.inference_seconds,
            negative_refusal_rate=sum(negative_refusals)/len(negative_refusals),
            queries=rows,
        )
        # Write evidence even on quality regression; never hide a failed sample.
        report = os.environ.get("DAY12_RERANK_REPORT_JSON")
        if report:
            with Path(report).open("x", encoding="utf-8") as handle:
                json.dump(summary, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
        print("DAY12_RERANK_COMPARISON_RESULT " + json.dumps(summary, ensure_ascii=False))
        _assert_quality_acceptance(rows)
    finally:
        try:
            try:
                if client.collection_exists(collection):
                    client.delete_collection(collection_name=collection)
                    assert not client.collection_exists(collection)
            finally:
                client.close()
        finally:
            _delete_document(factory, document_id)
