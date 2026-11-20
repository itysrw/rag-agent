"""Local evidence-gate replay: frozen PDFs, BGE, BM25/RRF and reranker; no LLM."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any, Sequence
from uuid import NAMESPACE_URL, UUID, uuid5

import numpy as np
from loguru import logger

from backend.app.core.config import (
    EmbeddingSettings, RAGSettings, RAG_MIN_RELEVANCE_SCORE, RAG_MIN_RERANKER_SCORE, RerankerSettings,
)
from backend.app.services.bm25 import BM25CorpusChunk, BM25Service
from backend.app.services.embedding import BGE_QUERY_INSTRUCTION, EmbeddingClient, load_embedding_model
from backend.app.services.hybrid import HYBRID_CANDIDATE_K, reciprocal_rank_fusion
from backend.app.services.qdrant_store import RetrievedChunk
from backend.app.services.rag import select_context_chunks, select_relevant_chunks
from backend.app.services.reranker import RERANK_FINAL_K, RerankOutcome, RerankedChunk, RerankerService
from backend.app.services.text_splitter import split_pages
from eval.chunk_comparison import _pages
from eval.real import _model_paths
from eval.scoring import DATASET_SHA256, MANIFEST_SHA256, EvalCase, EvalInputs, load_inputs

_O200K_CACHE_KEY = "fb374d419588a4632f3f557e76b4b70aebbca790"
_O200K_SHA256 = "446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d"


def collect_scores(inputs: EvalInputs) -> list[dict[str, Any]]:
    """Reproduce retrieval locally, with deterministic identities and exact cosine."""
    embedding_settings = EmbeddingSettings(_env_file=None, normalize_embeddings=True)
    reranker_settings = RerankerSettings(_env_file=None)
    embedding_path, reranker_path = _model_paths(embedding_settings, reranker_settings)
    model = load_embedding_model(embedding_path, embedding_settings)
    embedding = EmbeddingClient(
        embedding_settings, snapshot_resolver=lambda _: embedding_path,
        model_loader=lambda _path, _settings: model,
    )
    corpus = []
    for filename, pages in _pages(Path(__file__).resolve().parent, inputs.corpus).items():
        for draft in split_pages(pages, chunk_size=300, chunk_overlap=60, encoding_name="o200k_base"):
            corpus.append(BM25CorpusChunk(
                uuid5(NAMESPACE_URL, f"gate:{filename}:{draft.chunk_index}"),
                uuid5(NAMESPACE_URL, f"gate:{filename}"), draft.chunk_index,
                draft.content, draft.page, filename, dict(draft.metadata),
            ))
    corpus.sort(key=lambda item: (str(item.doc_id), item.chunk_index, str(item.chunk_id)))
    vectors = np.asarray(embedding.embed_documents([item.content for item in corpus]), dtype=np.float32)
    queries = np.asarray(embedding.embed_documents([
        BGE_QUERY_INSTRUCTION + case.question for case in inputs.cases
    ]), dtype=np.float32)
    scores = queries @ vectors.T
    bm25 = BM25Service(lambda: tuple(corpus))
    reranker = RerankerService(reranker_settings, snapshot_resolver=lambda _: reranker_path)
    rows = []
    for index, case in enumerate(inputs.cases):
        vector_results = [
            RetrievedChunk(**asdict(corpus[int(i)]), score=float(scores[index, int(i)]))
            for i in np.argsort(-scores[index], kind="stable")[:HYBRID_CANDIDATE_K]
        ]
        candidates = reciprocal_rank_fusion(
            vector_results, bm25.search(case.question, top_k=HYBRID_CANDIDATE_K),
            top_k=HYBRID_CANDIDATE_K,
        )
        outcome = reranker.rerank(case.question, candidates)
        rows.append({"id": case.id, "chunks": [asdict(chunk) for chunk in outcome.ranked_candidates]})
        if (index + 1) % 10 == 0 or index == 0:
            print(f"scored={index + 1}/{len(inputs.cases)}", flush=True)
    return rows


def decode_chunks(row: dict[str, Any]) -> tuple[RerankedChunk, ...]:
    """Restore only locally saved reranker output for a gate-only replay."""
    return tuple(RerankedChunk(**{
        **item, "chunk_id": UUID(str(item["chunk_id"])), "doc_id": UUID(str(item["doc_id"])),
    }) for item in row["chunks"])


def measure_gate(
    cases: Sequence[EvalCase], chunks_by_case: dict[str, tuple[RerankedChunk, ...]],
    gate: Callable[[tuple[RerankedChunk, ...]], Sequence[RerankedChunk]],
) -> dict[str, int | float]:
    """Count retained required pages and no-answer cases sent to generation."""
    answerable = unanswerable = hits = empty = unanswerable_admitted = kept_chunks = 0
    below_top5 = 0
    coverage = 0.0
    for case in cases:
        selected = gate(chunks_by_case[case.id])
        kept_chunks += len(selected)
        below_top5 += sum(chunk.rerank_rank > RERANK_FINAL_K for chunk in selected)
        expected = set(case.expected_sources)
        if expected:
            answerable += 1
            found = {(chunk.filename, chunk.page) for chunk in selected}
            hits += expected <= found
            coverage += len(expected & found) / len(expected)
            empty += not selected
        else:
            unanswerable += 1
            unanswerable_admitted += bool(selected)
    return {
        "answerable": answerable, "all_pages_hit": hits,
        "mean_page_coverage": round(coverage / answerable, 4),
        "answerable_without_context": empty, "unanswerable": unanswerable,
        "unanswerable_admitted": unanswerable_admitted, "total_context_chunks": kept_chunks,
        "chunks_below_top5": below_top5,
    }


def compare_gates(
    cases: Sequence[EvalCase], chunks_by_case: dict[str, tuple[RerankedChunk, ...]],
) -> dict[str, object]:
    """Compare both previous gates with the production selector on identical scores."""
    settings = RAGSettings(
        _env_file=None, min_relevance_score=RAG_MIN_RELEVANCE_SCORE,
        min_reranker_score=RAG_MIN_RERANKER_SCORE,
    )

    def vector_only(chunks: tuple[RerankedChunk, ...]) -> tuple[RerankedChunk, ...]:
        return select_relevant_chunks(chunks[:RERANK_FINAL_K], min_score=0.46)

    def top5_gate(chunks: tuple[RerankedChunk, ...]) -> tuple[RerankedChunk, ...]:
        return select_relevant_chunks(
            chunks[:RERANK_FINAL_K], min_score=RAG_MIN_RELEVANCE_SCORE,
            min_reranker_score=RAG_MIN_RERANKER_SCORE,
        )

    def page_selection(chunks: tuple[RerankedChunk, ...]) -> tuple[RerankedChunk, ...]:
        return select_context_chunks(RerankOutcome(chunks, (), len(chunks), 0), settings)

    gates = {"top5_candidates": lambda chunks: chunks[:RERANK_FINAL_K],
             "vector_only": vector_only, "top5_gate": top5_gate}
    if any(len(chunks) > RERANK_FINAL_K for chunks in chunks_by_case.values()):
        gates.update(all_candidates=tuple, page_selection=page_selection)
    return {
        name: {policy: measure_gate(subset, chunks_by_case, gate) for policy, gate in gates.items()}
        for name, subset in (("all", cases), ("odd", cases[::2]), ("even", cases[1::2]))
    }


def main(argv: Sequence[str] | None = None) -> None:
    """Collect local scores once, or replay gates on saved results."""
    parser = argparse.ArgumentParser(description=__doc__)
    paths = parser.add_mutually_exclusive_group(required=True)
    paths.add_argument("--output-dir", type=Path)
    paths.add_argument("--replay", type=Path)
    args = parser.parse_args(argv)
    logger.remove()
    inputs = load_inputs(Path(__file__).resolve().parent)
    if args.replay is not None:
        manifest = json.loads((args.replay / "manifest.json").read_bytes())
        content = (args.replay / "scores.jsonl").read_text(encoding="utf-8")
        if (manifest["dataset_sha256"] != DATASET_SHA256
                or manifest["corpus_manifest_sha256"] != MANIFEST_SHA256
                or manifest["scores_sha256"] != sha256(content.encode()).hexdigest()):
            raise ValueError("Replay hashes do not match the frozen inputs or captured scores.")
        rows = [json.loads(line) for line in content.splitlines()]
        if [row["id"] for row in rows] != [case.id for case in inputs.cases]:
            raise ValueError("Replay must contain every frozen case in order.")
        chunks = {row["id"]: decode_chunks(row) for row in rows}
        print(json.dumps(compare_gates(inputs.cases, chunks), indent=2))
        return

    token_cache = Path(os.environ.get("TIKTOKEN_CACHE_DIR") or Path("data/tiktoken-cache").resolve())
    token_file = token_cache / _O200K_CACHE_KEY
    if not token_file.is_file() or sha256(token_file.read_bytes()).hexdigest() != _O200K_SHA256:
        parser.error("Set TIKTOKEN_CACHE_DIR to a directory with the verified local o200k_base cache.")
    os.environ["TIKTOKEN_CACHE_DIR"] = str(token_cache.resolve())
    args.output_dir.mkdir(parents=True, exist_ok=False)
    rows = collect_scores(inputs)
    content = "".join(json.dumps(row, ensure_ascii=False, default=str) + "\n" for row in rows)
    (args.output_dir / "scores.jsonl").write_text(content, encoding="utf-8")
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset_sha256": DATASET_SHA256, "corpus_manifest_sha256": MANIFEST_SHA256,
        "scores_sha256": sha256(content.encode()).hexdigest(),
        "embedding_revision": EmbeddingSettings(_env_file=None).model_revision,
        "reranker_revision": RerankerSettings(_env_file=None).model_revision,
        "chunk_size": 300, "chunk_overlap": 60, "encoding_name": "o200k_base",
        "method": "local_exact_cosine_top20_production_bm25_rrf20_full_rerank_no_llm",
        "cases": len(rows), "paid_requests": 0,
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest))
    chunks = {row["id"]: decode_chunks(row) for row in rows}
    print(json.dumps(compare_gates(inputs.cases, chunks), indent=2))


if __name__ == "__main__":
    main()
