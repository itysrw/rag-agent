"""Deterministic Day 9 chunk-size experiment with opt-in real services.

The corpus contract, NFKC hit rule, and o200k token accounting run in the
standard suite.  Only the BGE/Qdrant retrieval experiment is opt-in.
"""

from __future__ import annotations

import json
import os
import statistics
import unicodedata
from dataclasses import asdict, dataclass
from uuid import uuid4

import pytest
import tiktoken
from qdrant_client import QdrantClient

from backend.app.core.config import PROJECT_ROOT, EmbeddingSettings, QdrantSettings
from backend.app.services.document_parser import PageText
from backend.app.services.embedding import EmbeddingClient
from backend.app.services.qdrant_store import QdrantVectorStore, VectorizedChunk
from backend.app.services.text_splitter import ChunkDraft, split_pages
from backend.tests.day9_tuning_corpus import CORPUS_PAGES, QUESTIONS, page_texts

pytestmark = pytest.mark.integration

ENCODING_NAME = "o200k_base"
TOP_K = 5
CHUNK_CONFIGS: tuple[tuple[int, int], ...] = (
    (300, 60),
    (500, 100),
    (800, 160),
)

requires_real_stack = pytest.mark.skipif(
    os.environ.get("RUN_QDRANT_INTEGRATION") != "1"
    or os.environ.get("RUN_LOCAL_EMBEDDING_INTEGRATION") != "1",
    reason="enable both real Qdrant and local BGE integration tests",
)


@dataclass(frozen=True, slots=True)
class ConfigReport:
    """Objective output for one real chunk configuration."""

    chunk_size: int
    chunk_overlap: int
    chunk_count: int
    avg_chunk_tokens: float
    top5_context_tokens_total: int
    max_chunk_tokens: int
    max_bge_tokens: int
    hit_at_1: float
    hit_at_5: float
    mrr_at_5: float


def normalized(text: str) -> str:
    """Apply the only permitted hit normalization: NFKC plus strip."""
    return unicodedata.normalize("NFKC", text).strip()


def chunk_hits_phrase(content: str, expected_phrase: str) -> bool:
    """Return whether normalized content contains the normalized phrase."""
    return normalized(expected_phrase) in normalized(content)


def token_count(encoding: tiktoken.Encoding, text: str) -> int:
    """Count the fixed cross-configuration o200k approximation unit."""
    return len(encoding.encode(text, disallowed_special=()))


def corpus_pages() -> list[PageText]:
    """Convert committed page constants into the production parser shape."""
    return [
        PageText(page=index, text=text)
        for index, text in enumerate(page_texts(), start=1)
    ]


def configuration_drafts() -> dict[tuple[int, int], list[ChunkDraft]]:
    """Split the same committed corpus under all three fixed configurations."""
    pages = corpus_pages()
    return {
        config: split_pages(
            pages,
            chunk_size=config[0],
            chunk_overlap=config[1],
            encoding_name=ENCODING_NAME,
        )
        for config in CHUNK_CONFIGS
    }


def build_embedding_client() -> EmbeddingClient:
    """Return the pinned local BGE client using the ignored model cache."""
    return EmbeddingClient(
        EmbeddingSettings(
            _env_file=None,
            cache_dir=PROJECT_ROOT / "data" / "models",
        )
    )


def build_qdrant_client(settings: QdrantSettings) -> QdrantClient:
    """Return the local Qdrant REST client used by disposable collections."""
    return QdrantClient(
        url=settings.build_url(),
        timeout=settings.timeout_seconds,
        prefer_grpc=False,
    )


def test_normalization_is_nfkc_and_outer_strip_only() -> None:
    """Compatibility characters normalize without lowercasing or inner edits."""
    assert normalized("  ＡＢＣ  ") == "ABC"
    assert normalized("  Ab C  ") == "Ab C"
    assert chunk_hits_phrase("制度规定：ＡＢＣ", "ABC") is True
    assert chunk_hits_phrase("制度规定：ABC", "abc") is False


def test_corpus_satisfies_the_patched_structural_contract() -> None:
    """Fail before BGE/Qdrant if the fixed corpus could invalidate the study."""
    encoding = tiktoken.get_encoding(ENCODING_NAME)
    texts = page_texts()

    assert len(QUESTIONS) >= 8
    assert len(texts) == len(CORPUS_PAGES)
    for question in QUESTIONS:
        assert set(question) == {"question", "expected_phrase"}
        assert question["question"].strip()
        assert question["expected_phrase"].strip()

    for page_index, (paragraphs, text) in enumerate(
        zip(CORPUS_PAGES, texts, strict=True),
        start=1,
    ):
        assert token_count(encoding, text) > 800, page_index
        assert len(paragraphs) == 5, page_index
        paragraph_tokens = [
            token_count(encoding, paragraph) for paragraph in paragraphs
        ]
        assert all(160 < count < 300 for count in paragraph_tokens), (
            page_index,
            paragraph_tokens,
        )

    for question in QUESTIONS:
        phrase = question["expected_phrase"]
        matching_pages = [
            page_index
            for page_index, text in enumerate(texts, start=1)
            if chunk_hits_phrase(text, phrase)
        ]
        assert len(matching_pages) == 1, (phrase, matching_pages)

    drafts_by_config = configuration_drafts()
    chunk_counts = [
        len(drafts_by_config[config]) for config in CHUNK_CONFIGS
    ]
    assert len(set(chunk_counts)) == len(CHUNK_CONFIGS), chunk_counts
    assert chunk_counts[0] > chunk_counts[1] > chunk_counts[2], chunk_counts

    for config, drafts in drafts_by_config.items():
        assert drafts, config
        for question in QUESTIONS:
            assert any(
                chunk_hits_phrase(draft.content, question["expected_phrase"])
                for draft in drafts
            ), (config, question)


@requires_real_stack
def test_chunk_size_configurations_produce_real_metrics() -> None:
    """Run all three configurations through real BGE and temporary Qdrant."""
    encoding = tiktoken.get_encoding(ENCODING_NAME)
    embedding_client = build_embedding_client()
    model = embedding_client._get_model()
    drafts_by_config = configuration_drafts()
    reports: list[ConfigReport] = []
    query_vectors = [
        embedding_client.embed_query(question["question"])
        for question in QUESTIONS
    ]

    for chunk_size, chunk_overlap in CHUNK_CONFIGS:
        drafts = drafts_by_config[(chunk_size, chunk_overlap)]
        chunk_tokens = [
            token_count(encoding, draft.content) for draft in drafts
        ]
        bge_tokens = [
            len(
                model.tokenizer.encode(
                    draft.content,
                    add_special_tokens=True,
                    truncation=False,
                )
            )
            for draft in drafts
        ]
        assert max(bge_tokens) <= model.max_seq_length, (
            chunk_size,
            max(bge_tokens),
            model.max_seq_length,
        )
        vectors = embedding_client.embed_documents(
            [draft.content for draft in drafts]
        )

        collection = f"day9_tuning_{chunk_size}_{uuid4().hex}"
        settings = QdrantSettings(
            _env_file=None,
            host="127.0.0.1",
            port=6333,
            collection=collection,
        )
        qdrant_client = build_qdrant_client(settings)
        store = QdrantVectorStore(settings, client=qdrant_client)
        doc_id = uuid4()
        vectorized = [
            VectorizedChunk(
                chunk_id=uuid4(),
                doc_id=doc_id,
                chunk_index=draft.chunk_index,
                content=draft.content,
                page=draft.page,
                filename="day9-handbook.txt",
                metadata={},
                vector=vector,
            )
            for draft, vector in zip(drafts, vectors, strict=True)
        ]

        ranks: list[int | None] = []
        top5_context_tokens_total = 0
        try:
            store.initialize_collection()
            assert store.upsert_chunks(vectorized) == len(vectorized)
            for question, query_vector in zip(
                QUESTIONS,
                query_vectors,
                strict=True,
            ):
                results = store.search(query_vector, limit=TOP_K)
                assert len(results) <= TOP_K, question["question"]
                rank = next(
                    (
                        position
                        for position, result in enumerate(results, start=1)
                        if chunk_hits_phrase(
                            result.content,
                            question["expected_phrase"],
                        )
                    ),
                    None,
                )
                ranks.append(rank)
                top5_context_tokens_total += sum(
                    token_count(encoding, result.content) for result in results
                )
        finally:
            if qdrant_client.collection_exists(collection):
                qdrant_client.delete_collection(collection_name=collection)
            qdrant_client.close()

        question_count = len(QUESTIONS)
        report = ConfigReport(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            chunk_count=len(drafts),
            avg_chunk_tokens=round(statistics.mean(chunk_tokens), 1),
            top5_context_tokens_total=top5_context_tokens_total,
            max_chunk_tokens=max(chunk_tokens),
            max_bge_tokens=max(bge_tokens),
            hit_at_1=round(
                sum(rank == 1 for rank in ranks) / question_count,
                3,
            ),
            hit_at_5=round(
                sum(rank is not None for rank in ranks) / question_count,
                3,
            ),
            mrr_at_5=round(
                sum(1 / rank for rank in ranks if rank is not None)
                / question_count,
                3,
            ),
        )
        assert 0.0 <= report.hit_at_1 <= report.hit_at_5 <= 1.0
        assert report.hit_at_1 <= report.mrr_at_5 <= report.hit_at_5
        reports.append(report)

    assert len(reports) == len(CHUNK_CONFIGS)
    assert len({report.chunk_count for report in reports}) == len(CHUNK_CONFIGS)
    summary = {
        "experiment": "day9_chunk_size_retrieval_quality",
        "token_unit": "tiktoken o200k_base disallowed_special=()",
        "top_k": TOP_K,
        "question_count": len(QUESTIONS),
        "corpus_pages": len(CORPUS_PAGES),
        "reports": [asdict(report) for report in reports],
    }
    print("\nDAY9_TUNING_RESULT " + json.dumps(summary, ensure_ascii=False))
