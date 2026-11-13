"""Objective page coverage for the offline chunk comparison."""

import numpy as np
import pytest

from eval.chunk_comparison import ComparisonChunk, score_vector_candidates
from eval.scoring import EvalCase


def test_vector_score_requires_all_expected_pages_and_applies_gate() -> None:
    cases = (
        EvalCase("qa_001", "cross_paragraph", "medium", "question", "answer",
                 (("a.pdf", 1), ("b.pdf", 2)), ()),
        EvalCase("qa_002", "unanswerable", "hard", "no answer", "refusal", (), ()),
    )
    chunks = (
        ComparisonChunk("a.pdf", 1, "first", 10, 12),
        ComparisonChunk("b.pdf", 2, "second", 20, 22),
    )
    queries = np.asarray([[1.0, 0.0], [1.0, 0.0]], dtype=np.float32)
    vectors = np.asarray([[0.8, 0.0], [0.4, 0.0]], dtype=np.float32)

    result = score_vector_candidates(cases, chunks, queries, vectors, top_k=2)

    assert result == {
        "answerable_questions": 1,
        "vector_topk_all_pages_hit": 1,
        "vector_gated_topk_all_pages_hit": 0,
        "vector_topk_mean_page_coverage": 1.0,
        "vector_gated_topk_mean_page_coverage": 0.5,
        "topk_o200k_context_tokens_all_questions": 60,
    }
    assert score_vector_candidates(cases, chunks, queries, vectors, top_k=1)["vector_topk_all_pages_hit"] == 0


def test_vector_score_rejects_mismatched_embedding_rows() -> None:
    case = EvalCase("qa_001", "simple_fact", "easy", "q", "a", (("a.pdf", 1),), ())
    chunk = ComparisonChunk("a.pdf", 1, "text", 10, 12)
    with pytest.raises(ValueError, match="rows"):
        score_vector_candidates([case], [chunk], np.zeros((2, 2)), np.zeros((1, 2)))
