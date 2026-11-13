"""Offline chunk-size comparison on the frozen Day 17 corpus and questions.

No database, Qdrant, hosted model, or network access is used. The reported
retrieval metric is a vector-only proxy, not the production RAG source_hit.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Sequence

import numpy as np

from backend.app.core.config import EmbeddingSettings, MAX_PDF_PAGES, PROJECT_ROOT, READ_CHUNK_SIZE
from backend.app.services.document_parser import PageText, parse_document
from backend.app.services.embedding import (
    BGE_QUERY_INSTRUCTION, EmbeddingClient, SentenceEmbeddingModel, load_embedding_model,
)
from backend.app.services.text_splitter import ChunkDraft, split_pages
from eval.scoring import DATASET_SHA256, MANIFEST_SHA256, CorpusDocument, EvalCase, load_inputs


CHUNK_CONFIGS: tuple[tuple[int, int], ...] = (
    (200, 40), (250, 50), (300, 60), (500, 100), (800, 160),
)
VECTOR_GATE = 0.46
TOP_K = 5


@dataclass(frozen=True, slots=True)
class ComparisonChunk:
    filename: str
    page: int
    content: str
    o200k_tokens: int
    bge_tokens: int


def _local_model_path(settings: EmbeddingSettings) -> Path:
    snapshot = (settings.cache_dir / "models--BAAI--bge-small-zh-v1.5"
                / "snapshots" / settings.model_revision).resolve()
    if not snapshot.is_dir():
        raise RuntimeError("Pinned local BGE snapshot is unavailable; no download attempted.")
    return snapshot


def _pages(eval_dir: Path, documents: Sequence[CorpusDocument]) -> dict[str, list[PageText]]:
    pages_by_file: dict[str, list[PageText]] = {}
    for document in documents:
        pages = parse_document(
            eval_dir / "corpus" / document.filename, ".pdf",
            max_pdf_pages=MAX_PDF_PAGES, read_chunk_size=READ_CHUNK_SIZE,
        )
        if len(pages) != document.page_count:
            raise RuntimeError(f"Frozen PDF page count changed: {document.filename}")
        pages_by_file[document.filename] = pages
    return pages_by_file


def _chunks(
    pages_by_file: dict[str, list[PageText]], model: SentenceEmbeddingModel,
    *, size: int, overlap: int,
) -> list[ComparisonChunk]:
    result: list[ComparisonChunk] = []
    for filename, pages in pages_by_file.items():
        drafts: list[ChunkDraft] = split_pages(
            pages, chunk_size=size, chunk_overlap=overlap, encoding_name="o200k_base",
        )
        for draft in drafts:
            token_ids = model.tokenizer.encode(
                draft.content, add_special_tokens=True, truncation=False,
            )
            result.append(ComparisonChunk(
                filename, draft.page, draft.content,
                int(draft.metadata["token_count"]), len(token_ids),
            ))
    return result


def score_vector_candidates(
    cases: Sequence[EvalCase], chunks: Sequence[ComparisonChunk],
    query_vectors: np.ndarray, chunk_vectors: np.ndarray,
    *, top_k: int = TOP_K, vector_gate: float = VECTOR_GATE,
) -> dict[str, int | float]:
    """Count exact required-page coverage in vector Top K, with/without gate."""
    if top_k < 1 or not chunks:
        raise ValueError("Top K and chunk set must be nonempty.")
    if query_vectors.shape[0] != len(cases) or chunk_vectors.shape[0] != len(chunks):
        raise ValueError("Embedding rows must match questions and chunks.")
    if query_vectors.ndim != 2 or chunk_vectors.ndim != 2 or query_vectors.shape[1] != chunk_vectors.shape[1]:
        raise ValueError("Embedding dimensions must match.")
    scores = query_vectors @ chunk_vectors.T
    answerable = 0
    candidate_hits = 0
    gate_hits = 0
    candidate_coverage = 0.0
    gate_coverage = 0.0
    top_context_tokens = 0
    for row_index, case in enumerate(cases):
        top = np.argsort(-scores[row_index], kind="stable")[:top_k]
        top_context_tokens += sum(chunks[int(index)].o200k_tokens for index in top)
        if not case.expected_sources:
            continue
        answerable += 1
        expected = set(case.expected_sources)
        found = {(chunks[int(index)].filename, chunks[int(index)].page) for index in top}
        gated = {(chunks[int(index)].filename, chunks[int(index)].page)
                 for index in top if scores[row_index, int(index)] >= vector_gate}
        candidate_hits += expected <= found
        gate_hits += expected <= gated
        candidate_coverage += len(expected & found) / len(expected)
        gate_coverage += len(expected & gated) / len(expected)
    if not answerable:
        raise ValueError("At least one answerable question is required.")
    return {
        "answerable_questions": answerable,
        "vector_topk_all_pages_hit": candidate_hits,
        "vector_gated_topk_all_pages_hit": gate_hits,
        "vector_topk_mean_page_coverage": round(candidate_coverage / answerable, 4),
        "vector_gated_topk_mean_page_coverage": round(gate_coverage / answerable, 4),
        "topk_o200k_context_tokens_all_questions": top_context_tokens,
    }


def run_comparison(eval_dir: Path | None = None) -> dict[str, object]:
    """Hash-check frozen inputs, preflight all sizes, and score feasible sizes."""
    root = eval_dir or Path(__file__).resolve().parent
    inputs = load_inputs(root)
    settings = EmbeddingSettings(_env_file=None, cache_dir=PROJECT_ROOT / "data" / "models")
    model_path = _local_model_path(settings)
    model = load_embedding_model(model_path, settings)
    max_bge_tokens = model.max_seq_length
    pages_by_file = _pages(root, inputs.corpus)
    client = EmbeddingClient(
        settings, snapshot_resolver=lambda _: model_path,
        model_loader=lambda _path, _settings: model,
    )
    query_vectors = np.asarray(client.embed_documents([
        BGE_QUERY_INSTRUCTION + case.question for case in inputs.cases
    ]), dtype=np.float32)
    configurations: list[dict[str, object]] = []
    for size, overlap in CHUNK_CONFIGS:
        chunks = _chunks(pages_by_file, model, size=size, overlap=overlap)
        invalid = sum(chunk.bge_tokens > max_bge_tokens for chunk in chunks)
        record: dict[str, object] = {
            "chunk_size": size, "chunk_overlap": overlap,
            "chunk_count": len(chunks),
            "max_o200k_tokens": max(chunk.o200k_tokens for chunk in chunks),
            "max_bge_tokens": max(chunk.bge_tokens for chunk in chunks),
            "over_bge_limit": invalid,
            "vector_metric_status": "ineligible" if invalid else "measured",
        }
        if not invalid:
            chunk_vectors = np.asarray(
                client.embed_documents([chunk.content for chunk in chunks]), dtype=np.float32,
            )
            record.update(score_vector_candidates(
                inputs.cases, chunks, query_vectors, chunk_vectors,
            ))
        configurations.append(record)
    return {
        "dataset_sha256": DATASET_SHA256,
        "corpus_manifest_sha256": MANIFEST_SHA256,
        "embedding_model": settings.model_name,
        "embedding_revision": settings.model_revision,
        "bge_max_tokens": max_bge_tokens,
        "method": "local_normalized_bge_cosine_top5_no_hybrid_no_rerank_no_llm",
        "configurations": configurations,
    }


def main() -> None:
    """Print aggregate JSON only; do not modify frozen inputs or services."""
    print(json.dumps(run_comparison(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
