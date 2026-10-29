"""Unit tests for Day 11 reciprocal-rank fusion and orchestration."""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any
from uuid import UUID, uuid4

import pytest
from loguru import logger

from backend.app.core.logging import JSONL_LOG_MARKER
from backend.app.services.bm25 import BM25RetrievedChunk
from backend.app.services.hybrid import (
    HYBRID_CANDIDATE_K,
    HYBRID_SEARCH_EVENT,
    RRF_RANK_CONSTANT,
    HybridResultError,
    HybridRetrievalService,
    reciprocal_rank_fusion,
)
from backend.app.services.qdrant_store import RetrievedChunk


def vector_chunk(
    *,
    chunk_id: UUID | None = None,
    doc_id: UUID | None = None,
    chunk_index: int = 0,
    content: str = "VPN 故障联系网络组，服务分机是 6203。",
    page: int = 1,
    filename: str = "policy.pdf",
    metadata: dict[str, Any] | None = None,
    score: float = 0.91,
) -> RetrievedChunk:
    """Return one complete vector result."""
    return RetrievedChunk(
        chunk_id=chunk_id or uuid4(),
        doc_id=doc_id or uuid4(),
        chunk_index=chunk_index,
        content=content,
        page=page,
        filename=filename,
        metadata={} if metadata is None else metadata,
        score=score,
    )


def bm25_chunk(
    source: RetrievedChunk | None = None,
    *,
    score: float = 3.7,
) -> BM25RetrievedChunk:
    """Return one BM25 result with payload copied from a vector result."""
    resolved = source or vector_chunk()
    return BM25RetrievedChunk(
        chunk_id=resolved.chunk_id,
        doc_id=resolved.doc_id,
        chunk_index=resolved.chunk_index,
        content=resolved.content,
        page=resolved.page,
        filename=resolved.filename,
        metadata=dict(resolved.metadata),
        score=score,
    )


def test_rrf_uses_one_based_ranks_and_accumulates_both_branches() -> None:
    """Shared Chunks receive both contributions and branch-only Chunks remain."""
    vector_only = vector_chunk(chunk_id=UUID(int=1), doc_id=UUID(int=1))
    shared = vector_chunk(chunk_id=UUID(int=2), doc_id=UUID(int=1), chunk_index=1)
    bm25_only = vector_chunk(chunk_id=UUID(int=3), doc_id=UUID(int=1), chunk_index=2)

    results = reciprocal_rank_fusion(
        [vector_only, shared],
        [bm25_chunk(shared), bm25_chunk(bm25_only)],
        top_k=3,
    )

    assert [result.chunk_id for result in results] == [
        shared.chunk_id,
        vector_only.chunk_id,
        bm25_only.chunk_id,
    ]
    assert results[0].score == pytest.approx(1 / 62 + 1 / 61)
    assert results[0].vector_score == shared.score
    assert results[0].bm25_score == 3.7
    assert results[1].bm25_score is None
    assert results[2].vector_score is None
    assert (results[0].vector_rank, results[0].bm25_rank) == (2, 1)
    assert results[1].score == pytest.approx(1 / 61)
    assert results[2].score == pytest.approx(1 / 62)


def test_original_branch_scores_do_not_affect_fusion() -> None:
    """Cosine and BM25 score magnitudes never enter the RRF calculation."""
    first = vector_chunk(chunk_id=UUID(int=1), doc_id=UUID(int=1), score=-99.0)
    second = vector_chunk(chunk_id=UUID(int=2), doc_id=UUID(int=1), score=999.0)
    low_bm25 = bm25_chunk(second, score=-1000.0)

    baseline = reciprocal_rank_fusion([first, second], [low_bm25], top_k=2)
    changed = reciprocal_rank_fusion(
        [replace(first, score=1e20), replace(second, score=-1e20)],
        [replace(low_bm25, score=1e30)],
        top_k=2,
    )

    assert [(item.chunk_id, item.score) for item in baseline] == [
        (item.chunk_id, item.score) for item in changed
    ]


@pytest.mark.parametrize("branch", ["vector", "bm25"])
def test_duplicate_chunk_id_within_one_branch_is_rejected(branch: str) -> None:
    """A malformed branch cannot contribute the same rank identity twice."""
    chunk = vector_chunk()
    vector_results = [chunk, chunk] if branch == "vector" else []
    bm25_results = [bm25_chunk(chunk), bm25_chunk(chunk)] if branch == "bm25" else []

    with pytest.raises(HybridResultError, match="duplicate Chunk identity"):
        reciprocal_rank_fusion(vector_results, bm25_results, top_k=5)


@pytest.mark.parametrize(
    "changed",
    [
        {"doc_id": uuid4()},
        {"chunk_index": 9},
        {"content": "conflicting content"},
        {"page": 9},
        {"filename": "other.pdf"},
        {"metadata": {"conflict": True}},
    ],
)
def test_cross_store_payload_conflict_is_rejected(changed: dict[str, Any]) -> None:
    """The same Chunk UUID must describe exactly one retrieval-visible payload."""
    vector = vector_chunk(metadata={"a": 1})
    bm25 = replace(bm25_chunk(vector), **changed)

    with pytest.raises(HybridResultError, match="payloads do not match"):
        reciprocal_rank_fusion([vector], [bm25], top_k=5)


def test_metadata_key_order_is_not_a_payload_conflict() -> None:
    """Equivalent JSON objects remain consistent regardless of insertion order."""
    vector = vector_chunk(metadata={"b": 2, "a": 1})
    bm25 = replace(bm25_chunk(vector), metadata={"a": 1, "b": 2})

    results = reciprocal_rank_fusion([vector], [bm25], top_k=5)

    assert [result.chunk_id for result in results] == [vector.chunk_id]


@pytest.mark.parametrize("other_value", [True, 1.0])
def test_metadata_equal_values_with_different_types_are_conflicts(
    other_value: bool | float,
) -> None:
    """Python's True == 1 == 1.0 must not hide different JSON payloads."""
    vector = vector_chunk(metadata={"token_count": 1})
    bm25 = replace(bm25_chunk(vector), metadata={"token_count": other_value})

    with pytest.raises(HybridResultError, match="payloads do not match"):
        reciprocal_rank_fusion([vector], [bm25], top_k=5)


def test_identical_content_with_distinct_chunk_ids_is_not_deduplicated() -> None:
    """Chunk UUID, rather than content, page, or filename, is the fusion identity."""
    first = vector_chunk(chunk_id=UUID(int=1), doc_id=UUID(int=1))
    second = replace(first, chunk_id=UUID(int=2))

    results = reciprocal_rank_fusion([first], [bm25_chunk(second)], top_k=5)

    assert {result.chunk_id for result in results} == {UUID(int=1), UUID(int=2)}


def test_equal_rrf_scores_use_stable_identity_order() -> None:
    """Ties use best rank and stable payload identities, never raw scores."""
    later = vector_chunk(
        chunk_id=UUID(int=4),
        doc_id=UUID(int=2),
        chunk_index=0,
    )
    earlier = vector_chunk(
        chunk_id=UUID(int=3),
        doc_id=UUID(int=1),
        chunk_index=1,
    )

    results = reciprocal_rank_fusion(
        [later],
        [bm25_chunk(earlier)],
        top_k=5,
    )

    assert [result.chunk_id for result in results] == [earlier.chunk_id, later.chunk_id]


@pytest.mark.parametrize("top_k", [0, 21, True, "5", 5.0, None])
def test_rrf_rejects_invalid_top_k(top_k: Any) -> None:
    """The pure function shares the strict Day 9 result-limit contract."""
    with pytest.raises(ValueError):
        reciprocal_rank_fusion([], [], top_k=top_k)


@pytest.mark.parametrize("rank_constant", [0, -1, True, 60.0, "60"])
def test_rrf_rejects_invalid_rank_constant(rank_constant: Any) -> None:
    """Only a positive integer can define the reciprocal-rank denominator."""
    with pytest.raises(ValueError):
        reciprocal_rank_fusion(
            [],
            [],
            top_k=5,
            rank_constant=rank_constant,
        )


class StubBranchService:
    """Record branch calls and return or raise a controlled outcome."""

    def __init__(
        self,
        results: list[Any] | None = None,
        failure: BaseException | None = None,
    ) -> None:
        self.results = [] if results is None else results
        self.failure = failure
        self.calls: list[dict[str, Any]] = []

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        doc_id: UUID | None = None,
    ) -> list[Any]:
        self.calls.append({"query": query, "top_k": top_k, "doc_id": doc_id})
        if self.failure is not None:
            raise self.failure
        return self.results


def test_hybrid_service_uses_fixed_candidates_and_final_top_k() -> None:
    """Both branches receive 20 candidates while the response honors final top_k."""
    first = vector_chunk(chunk_id=UUID(int=1), doc_id=UUID(int=10))
    second = vector_chunk(chunk_id=UUID(int=2), doc_id=UUID(int=10), chunk_index=1)
    vector_service = StubBranchService([first, second])
    bm25_service = StubBranchService([bm25_chunk(second)])
    service = HybridRetrievalService(  # type: ignore[arg-type]
        vector_service,
        bm25_service,
    )
    doc_id = UUID(int=10)

    results = service.search("VPN 6203", top_k=1, doc_id=doc_id)

    expected_call = {
        "query": "VPN 6203",
        "top_k": HYBRID_CANDIDATE_K,
        "doc_id": doc_id,
    }
    assert vector_service.calls == [expected_call]
    assert bm25_service.calls == [expected_call]
    assert len(results) == 1
    assert results[0].chunk_id == second.chunk_id
    assert HYBRID_CANDIDATE_K == 20
    assert RRF_RANK_CONSTANT == 60


@pytest.mark.parametrize("top_k", [0, 21, True, "5", 5.0, None])
def test_hybrid_service_rejects_invalid_top_k_before_branch_calls(
    top_k: Any,
) -> None:
    """Invalid direct calls cannot trigger embedding, Qdrant, or PostgreSQL work."""
    vector_service = StubBranchService()
    bm25_service = StubBranchService()
    service = HybridRetrievalService(  # type: ignore[arg-type]
        vector_service,
        bm25_service,
    )

    with pytest.raises(ValueError):
        service.search("query", top_k=top_k)

    assert vector_service.calls == []
    assert bm25_service.calls == []


def test_hybrid_service_rejects_invalid_doc_id_before_branch_calls() -> None:
    """The service validates identity input before either branch is called."""
    vector_service = StubBranchService()
    bm25_service = StubBranchService()
    service = HybridRetrievalService(  # type: ignore[arg-type]
        vector_service,
        bm25_service,
    )

    with pytest.raises(ValueError):
        service.search("query", doc_id="not-a-uuid")  # type: ignore[arg-type]

    assert vector_service.calls == []
    assert bm25_service.calls == []


def test_vector_failure_stops_before_bm25_and_does_not_log_completion() -> None:
    """A failed first branch cannot silently degrade to a BM25-only response."""
    vector_service = StubBranchService(failure=RuntimeError("vector failed"))
    bm25_service = StubBranchService()
    service = HybridRetrievalService(  # type: ignore[arg-type]
        vector_service,
        bm25_service,
    )
    messages: list[str] = []
    handler_id = logger.add(lambda message: messages.append(message.record["message"]))
    try:
        with pytest.raises(RuntimeError, match="vector failed"):
            service.search("query")
    finally:
        logger.remove(handler_id)

    assert len(vector_service.calls) == 1
    assert bm25_service.calls == []
    assert not any(HYBRID_SEARCH_EVENT in message for message in messages)


def test_bm25_failure_does_not_return_vector_results_or_log_completion() -> None:
    """A failed second branch fails the whole operation after the vector call."""
    vector_service = StubBranchService([vector_chunk()])
    bm25_service = StubBranchService(failure=RuntimeError("bm25 failed"))
    service = HybridRetrievalService(  # type: ignore[arg-type]
        vector_service,
        bm25_service,
    )
    messages: list[str] = []
    handler_id = logger.add(lambda message: messages.append(message.record["message"]))
    try:
        with pytest.raises(RuntimeError, match="bm25 failed"):
            service.search("query")
    finally:
        logger.remove(handler_id)

    assert len(vector_service.calls) == 1
    assert len(bm25_service.calls) == 1
    assert not any(HYBRID_SEARCH_EVENT in message for message in messages)


def test_hybrid_log_contains_ranks_without_sensitive_or_branch_score_data() -> None:
    """One successful search emits only the approved Hybrid summary fields."""
    chunk = vector_chunk(
        content="private-content VPN",
        metadata={"secret": "private-metadata"},
        score=0.876543,
    )
    service = HybridRetrievalService(  # type: ignore[arg-type]
        StubBranchService([chunk]),
        StubBranchService([bm25_chunk(chunk, score=123.456)]),
    )
    messages: list[tuple[str, dict[str, Any]]] = []
    handler_id = logger.add(
        lambda message: messages.append(
            (message.record["message"], message.record["extra"])
        )
    )
    try:
        service.search("private-query VPN")
    finally:
        logger.remove(handler_id)

    events = [
        (json.loads(message), extra)
        for message, extra in messages
        if HYBRID_SEARCH_EVENT in message
    ]
    assert len(events) == 1
    event, extra = events[0]
    assert extra[JSONL_LOG_MARKER] is True
    assert event["candidate_k"] == 20
    assert event["rrf_rank_constant"] == 60
    assert event["results"][0]["vector_rank"] == 1
    assert event["results"][0]["bm25_rank"] == 1
    raw = json.dumps(event, ensure_ascii=False)
    for forbidden in (
        "private-query",
        "private-content",
        "private-metadata",
        "0.876543",
        "123.456",
        '"content"',
        '"metadata"',
        '"query_tokens"',
        '"vector_score"',
        '"bm25_score"',
    ):
        assert forbidden not in raw


def test_empty_hybrid_result_is_successfully_logged() -> None:
    """Two empty branches still produce one completed Hybrid event."""
    service = HybridRetrievalService(  # type: ignore[arg-type]
        StubBranchService(),
        StubBranchService(),
    )
    messages: list[str] = []
    handler_id = logger.add(lambda message: messages.append(message.record["message"]))
    try:
        assert service.search("unknown") == []
    finally:
        logger.remove(handler_id)

    events = [json.loads(message) for message in messages if HYBRID_SEARCH_EVENT in message]
    assert len(events) == 1
    assert events[0]["vector_result_count"] == 0
    assert events[0]["bm25_result_count"] == 0
    assert events[0]["result_count"] == 0


@pytest.mark.parametrize("top_k", [1, 5, 20])
def test_final_limit_does_not_change_branch_candidate_depth(top_k: int) -> None:
    """A caller can ask for 1, 5, or 20 while both branches still retrieve 20."""
    chunks = [
        vector_chunk(chunk_id=UUID(int=index + 1), chunk_index=index)
        for index in range(20)
    ]
    vector_service = StubBranchService(chunks)
    bm25_service = StubBranchService([bm25_chunk(chunk) for chunk in chunks])
    service = HybridRetrievalService(  # type: ignore[arg-type]
        vector_service, bm25_service
    )

    results = service.search("VPN", top_k=top_k)

    assert len(results) == top_k
    assert [item.chunk_id for item in results] == [
        item.chunk_id for item in chunks[:top_k]
    ]
    assert vector_service.calls[0]["top_k"] == 20
    assert bm25_service.calls[0]["top_k"] == 20


def test_fusion_does_not_mutate_inputs_or_share_metadata() -> None:
    """Caller-owned branch payloads remain unchanged after fusion."""
    chunk = vector_chunk(metadata={"token_count": 12})
    vector_results = [chunk]
    bm25_results = [bm25_chunk(chunk)]

    results = reciprocal_rank_fusion(vector_results, bm25_results, top_k=5)
    results[0].metadata["token_count"] = 99

    assert vector_results == [chunk]
    assert chunk.metadata == {"token_count": 12}
    assert bm25_results[0].metadata == {"token_count": 12}


def test_log_serialization_failure_is_safe_and_does_not_fail_search(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A broken log serializer neither leaks its exception nor loses results."""
    def fail_serialization(*args: Any, **kwargs: Any) -> str:
        raise ValueError("private-serialization-detail")

    chunk = vector_chunk()
    service = HybridRetrievalService(  # type: ignore[arg-type]
        StubBranchService([chunk]), StubBranchService([bm25_chunk(chunk)])
    )
    messages: list[str] = []
    handler = logger.add(lambda message: messages.append(message.record["message"]))
    monkeypatch.setattr("backend.app.services.hybrid.json.dumps", fail_serialization)
    try:
        results = service.search("private-query")
    finally:
        logger.remove(handler)

    assert [item.chunk_id for item in results] == [chunk.chunk_id]
    assert messages == ["Hybrid search event serialization failed."]
