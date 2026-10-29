"""Offline contract tests for local reranking, lengths, identity, and logs."""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import httpx
import pytest
from huggingface_hub.errors import LocalEntryNotFoundError
from loguru import logger
from pydantic import ValidationError

from backend.app.core.config import PROJECT_ROOT, RerankerSettings
from backend.app.core.logging import JSONL_LOG_MARKER
from backend.app.services.hybrid import HybridResultError, HybridRetrievedChunk
from backend.app.services.reranker import (
    MODEL_FILES, PassageOnlyTokenizer, RerankedRetrievalService, RerankerInputError,
    RerankerResultError, RerankerService, RerankerUnavailableError,
    ensure_reranker_snapshot, load_reranker_model, rank_candidates,
)


def candidates(count: int = 20) -> list[HybridRetrievedChunk]:
    """Distinct identities intentionally share content."""
    return [HybridRetrievedChunk(
        chunk_id=UUID(int=i+1), doc_id=UUID(int=100), chunk_index=i,
        content="private-passage VPN", page=i+1, filename="private.pdf",
        metadata={"private": "metadata"}, score=0.03-i/10000,
        vector_rank=i+1, bm25_rank=i+1, vector_score=0.8, bm25_score=9.0,
    ) for i in range(count)]


class FakeTokenizer:
    """Character tokenizer makes preserved queries and passage cuts observable."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.encoded_pairs: list[tuple[str, str]] = []

    def encode(self, text: str, **kwargs: Any) -> list[int]:
        return list(range(len(text)))

    def num_special_tokens_to_add(self, *, pair: bool) -> int:
        return 4

    def __call__(self, pairs: list[tuple[str, str]], **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        result = []
        for query, passage in pairs:
            if kwargs.get("truncation") == "only_second":
                passage = passage[:kwargs["max_length"]-len(query)-4]
                self.encoded_pairs.append((query, passage))
            result.append(list(range(len(query)+len(passage)+4)))
        return {"input_ids": result}


class FakeModel:
    """Simulate CrossEncoder's tokenizer call without a neural model."""

    def __init__(self, scores: Any = None) -> None:
        self.original_tokenizer = FakeTokenizer()
        self.tokenizer = PassageOnlyTokenizer(self.original_tokenizer, 512)
        self.scores = scores
        self.calls: list[tuple[list[tuple[str, str]], dict[str, Any]]] = []

    def predict(self, pairs: list[tuple[str, str]], **kwargs: Any) -> Any:
        self.calls.append((pairs, kwargs))
        self.tokenizer(pairs, padding=True, truncation=True, return_tensors="pt")
        return list(range(len(pairs))) if self.scores is None else self.scores


def service(model: FakeModel) -> RerankerService:
    """Inject all IO boundaries."""
    return RerankerService(RerankerSettings(_env_file=None),
        snapshot_resolver=lambda _: Path("unused"), model_loader=lambda *_: model)


@pytest.mark.parametrize("count", [0, 1, 4, 5, 20])
def test_all_candidates_scored_then_fixed_five_returned(count: int) -> None:
    model = FakeModel()
    outcome = service(model).rerank("  VPN 中文 question  ", candidates(count))
    assert len(outcome.results) == min(count, 5)
    assert len(outcome.movements) == count
    assert outcome.candidate_count == count
    assert len({item.chunk_id for item in outcome.results}) == min(count, 5)
    if count:
        assert len(model.calls[0][0]) == count
        assert model.calls[0][0][0][0] == "VPN 中文 question"
        assert type(model.calls[0][1]["activation_fn"]).__name__ == "Identity"
        assert model.calls[0][1]["show_progress_bar"] is False
        assert outcome.results[0].hybrid_rank == count
        assert outcome.results[0].rank_change == count-1
    else:
        assert model.calls == []


def test_empty_input_does_not_resolve_or_load_model() -> None:
    def forbidden(*args: Any) -> Any:
        raise AssertionError("model must remain lazy")
    reranker = RerankerService(RerankerSettings(_env_file=None), snapshot_resolver=forbidden)
    assert reranker.rerank("query", []).results == ()


def test_truncation_protects_query_and_records_candidate_count() -> None:
    model = FakeModel()
    items = candidates(2)
    items[0] = replace(items[0], content="passage" * 200)
    outcome = service(model).rerank("完整 query", items)
    assert outcome.truncated_candidate_count == 1
    assert model.original_tokenizer.calls[-1]["truncation"] == "only_second"
    assert model.original_tokenizer.encoded_pairs[0][0] == "完整 query"
    assert len(model.original_tokenizer.encoded_pairs[0][1]) == 512-len("完整 query")-4


def test_oversized_query_is_rejected_before_predict() -> None:
    model = FakeModel()
    with pytest.raises(RerankerInputError):
        service(model).rerank("q" * 508, candidates(1))
    assert model.calls == []


def test_ties_keep_hybrid_order_and_do_not_mutate_metadata() -> None:
    items = candidates(6)
    outcome = rank_candidates(items, [-8.0] * 6)
    assert [item.chunk_id for item in outcome.results] == [item.chunk_id for item in items[:5]]
    assert all(item.rank_change == 0 for item in outcome.movements)
    outcome.results[0].metadata["private"] = "changed"
    assert items[0].metadata["private"] == "metadata"


@pytest.mark.parametrize("scores", [[1.0], [float("nan"), 0], [float("inf"), 0], [True, 0], [[1.0], [2.0]], "bad"])
def test_invalid_model_scores_are_rejected(scores: Any) -> None:
    with pytest.raises(RerankerResultError):
        service(FakeModel(scores)).rerank("query", candidates(2))


def test_duplicate_and_excess_candidates_fail_before_loading() -> None:
    model = FakeModel()
    item = candidates(1)[0]
    with pytest.raises(HybridResultError):
        service(model).rerank("query", [item, item])
    with pytest.raises(RerankerResultError):
        service(model).rerank("query", candidates(21))
    assert model.calls == []


def test_model_is_loaded_once_and_warm_calls_report_no_load_time() -> None:
    loads: list[bool] = []
    def loader(*args: Any) -> FakeModel:
        loads.append(True)
        return FakeModel()
    reranker = RerankerService(RerankerSettings(_env_file=None),
        snapshot_resolver=lambda _: Path("unused"), model_loader=loader)
    reranker.rerank("query", candidates(1))
    assert reranker.rerank("query", candidates(1)).model_load_seconds == 0
    assert loads == [True]


@pytest.mark.parametrize("changed", [
    {"model_name": "other"}, {"model_revision": "main"}, {"device": "cuda"},
    {"max_length": 1024}, {"batch_size": 0}, {"batch_size": 9},
    {"batch_size": True}, {"download_max_retries": 4},
])
def test_settings_pin_model_and_bound_resources(changed: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        RerankerSettings(_env_file=None, **changed)


def test_cache_path_is_project_relative() -> None:
    assert RerankerSettings(_env_file=None, cache_dir=Path("data/test-reranker")).cache_dir == PROJECT_ROOT / "data/test-reranker"


def test_batch_size_can_be_configured_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RERANKER_BATCH_SIZE", "4")
    assert RerankerSettings(_env_file=None).batch_size == 4


def test_load_and_inference_failures_are_safe() -> None:
    def failing_loader(*args: Any) -> Any:
        raise OSError("private-cache-path")
    reranker = RerankerService(RerankerSettings(_env_file=None),
        snapshot_resolver=lambda _: Path("unused"), model_loader=failing_loader)
    with pytest.raises(RerankerUnavailableError, match="could not be loaded") as error:
        reranker.rerank("query", candidates(1))
    assert "private-cache-path" not in str(error.value)
    class BrokenModel(FakeModel):
        def predict(self, *args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("private-inference-detail")
    with pytest.raises(RerankerUnavailableError, match="inference failed") as error:
        service(BrokenModel()).rerank("query", candidates(1))
    assert "private-inference-detail" not in str(error.value)


def test_download_retries_transient_errors_and_requests_only_safe_files(tmp_path: Path) -> None:
    settings = RerankerSettings(_env_file=None, cache_dir=tmp_path)
    attempts: list[dict[str, Any]] = []
    delays: list[float] = []
    def download(**kwargs: Any) -> str:
        attempts.append(kwargs)
        if kwargs["local_files_only"]:
            raise LocalEntryNotFoundError("not cached")
        if len(attempts) == 2:
            raise httpx.ConnectError("private network detail")
        for name in MODEL_FILES:
            (tmp_path / name).write_text("fake", encoding="utf-8")
        return str(tmp_path)
    assert ensure_reranker_snapshot(settings, downloader=download, sleep=delays.append) == tmp_path
    assert delays == [1.0]
    assert attempts[0]["token"] is False
    assert attempts[0]["revision"] == settings.model_revision
    assert set(attempts[0]["allow_patterns"]) == set(MODEL_FILES)


def test_download_retries_read_errors_with_exponential_backoff(
    tmp_path: Path,
) -> None:
    """Interrupted response bodies receive the full bounded retry policy."""
    attempts: list[bool] = []
    delays: list[float] = []

    def download(**kwargs: Any) -> str:
        attempts.append(kwargs["local_files_only"])
        if kwargs["local_files_only"]:
            raise LocalEntryNotFoundError("not cached")
        raise httpx.ReadError("private interrupted response")

    with pytest.raises(
        RerankerUnavailableError,
        match="snapshot is unavailable",
    ) as error:
        ensure_reranker_snapshot(
            RerankerSettings(_env_file=None, cache_dir=tmp_path),
            downloader=download,
            sleep=delays.append,
        )

    assert attempts == [True, False, False, False, False]
    assert delays == [1.0, 2.0, 4.0]
    assert "private interrupted response" not in str(error.value)


def test_download_does_not_retry_permanent_failure(tmp_path: Path) -> None:
    attempts: list[bool] = []
    def download(**kwargs: Any) -> str:
        attempts.append(kwargs["local_files_only"])
        if kwargs["local_files_only"]:
            raise LocalEntryNotFoundError("not cached")
        raise ValueError("private failure")
    with pytest.raises(RerankerUnavailableError, match="snapshot is unavailable"):
        ensure_reranker_snapshot(RerankerSettings(_env_file=None, cache_dir=tmp_path), downloader=download)
    assert attempts == [True, False]


def test_loader_requires_local_cpu_safetensors_and_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []
    def cross_encoder(path: str, **kwargs: Any) -> Any:
        calls.append(kwargs)
        return SimpleNamespace(config=SimpleNamespace(num_labels=1), tokenizer=FakeTokenizer())
    monkeypatch.setitem(sys.modules, "sentence_transformers", SimpleNamespace(CrossEncoder=cross_encoder))
    model = load_reranker_model(Path("unused"), RerankerSettings(_env_file=None))
    assert isinstance(model.tokenizer, PassageOnlyTokenizer)
    assert calls[0]["device"] == "cpu"
    assert calls[0]["local_files_only"] is True
    assert calls[0]["trust_remote_code"] is False
    assert calls[0]["model_kwargs"] == {"use_safetensors": True}
    assert type(calls[0]["activation_fn"]).__name__ == "Identity"


def test_pipeline_fixed_depth_filter_and_complete_safe_log() -> None:
    items = candidates()
    calls: list[dict[str, Any]] = []
    class Hybrid:
        def search(self, query: str, **kwargs: Any) -> list[HybridRetrievedChunk]:
            calls.append(kwargs)
            return items
    pipeline = RerankedRetrievalService(Hybrid(), service(FakeModel()))  # type: ignore[arg-type]
    messages: list[Any] = []
    handler = logger.add(lambda message: messages.append(message.record))
    try:
        result = pipeline.search("private-query", doc_id=UUID(int=100))
    finally:
        logger.remove(handler)
    assert calls == [{"top_k": 20, "doc_id": UUID(int=100)}]
    assert len(result.results) == 5
    record = next(item for item in messages if "rerank_search_completed" in item["message"])
    event = json.loads(record["message"])
    assert record["extra"][JSONL_LOG_MARKER] is True
    assert len(event["movements"]) == 20
    assert event["candidate_count"] == 20
    for forbidden in ("private-query", "private-passage", "metadata", "private.pdf"):
        assert forbidden not in record["message"]
