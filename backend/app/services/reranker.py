"""Pinned local reranking: Hybrid Top-20 to five scored, traceable Chunks."""

from __future__ import annotations

import hashlib
import json
import math
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from functools import lru_cache
from numbers import Real
from pathlib import Path
from threading import Lock
from typing import Any, Protocol
from uuid import UUID

import httpx
from huggingface_hub import snapshot_download
from huggingface_hub.errors import HfHubHTTPError, LocalEntryNotFoundError
from loguru import logger

from backend.app.core.config import RerankerSettings, get_reranker_settings
from backend.app.core.logging import JSONL_LOG_MARKER
from backend.app.models.chunk import JSONScalar
from backend.app.services.hybrid import (
    HYBRID_CANDIDATE_K,
    HybridResultError,
    HybridRetrievedChunk,
    HybridRetrievalService,
    get_hybrid_retrieval_service,
)

RERANK_FINAL_K = 5
RERANK_SEARCH_EVENT = "rerank_search_completed"
MODEL_FILES = (
    "config.json",
    "model.safetensors",
    "sentencepiece.bpe.model",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
)


class RerankerError(RuntimeError):
    """Base safe reranker failure."""


class RerankerUnavailableError(RerankerError):
    """The pinned local model cannot be downloaded, loaded, or executed."""


class RerankerInputError(RerankerError):
    """The complete query cannot fit without truncating its meaning."""


class RerankerResultError(RerankerError):
    """The model returned invalid scores or the candidate set is invalid."""


class CrossEncoderModel(Protocol):
    """Small injectable boundary; importing the app does not import Torch."""

    tokenizer: Any

    def predict(self, sentences: list[tuple[str, str]], **kwargs: Any) -> Any: ...


@dataclass(frozen=True, slots=True)
class RerankedChunk:
    """One candidate with raw logit and separate internal retrieval evidence."""

    chunk_id: UUID
    doc_id: UUID
    chunk_index: int
    content: str
    page: int
    filename: str
    metadata: dict[str, JSONScalar]
    score: float
    hybrid_score: float
    hybrid_rank: int
    rerank_rank: int
    rank_change: int
    vector_score: float | None
    vector_rank: int | None
    bm25_rank: int | None


@dataclass(frozen=True, slots=True)
class RankMovement:
    """All-candidate ranking evidence safe to include in JSONL."""

    chunk_id: str
    doc_id: str
    hybrid_rank: int
    rerank_rank: int
    rank_change: int
    reranker_score: float


@dataclass(frozen=True, slots=True)
class RerankOutcome:
    """Top five plus the complete movement and timing summary."""

    results: tuple[RerankedChunk, ...]
    movements: tuple[RankMovement, ...]
    candidate_count: int
    truncated_candidate_count: int
    model_load_seconds: float = 0.0
    inference_seconds: float = 0.0


def _snapshot_complete(path: Path) -> bool:
    return all(
        (path / name).is_file() and (path / name).stat().st_size > 0
        for name in MODEL_FILES
    )


def ensure_reranker_snapshot(
    settings: RerankerSettings,
    *,
    downloader: Callable[..., Any] = snapshot_download,
    sleep: Callable[[float], None] = time.sleep,
) -> Path:
    """Resolve only the pinned safe files, with bounded transient retries."""
    try:
        settings.cache_dir.mkdir(parents=True, exist_ok=True)
        arguments = dict(
            repo_id=settings.model_name,
            revision=settings.model_revision,
            cache_dir=settings.cache_dir,
            token=False,
            allow_patterns=list(MODEL_FILES),
        )
        try:
            cached = Path(downloader(**arguments, local_files_only=True))
            if _snapshot_complete(cached):
                return cached
        except LocalEntryNotFoundError:
            pass
        for attempt in range(settings.download_max_retries + 1):
            try:
                path = Path(downloader(**arguments, local_files_only=False))
                if not _snapshot_complete(path):
                    raise RerankerUnavailableError(
                        "The pinned reranker snapshot is incomplete."
                    )
                return path
            except (httpx.TransportError, HfHubHTTPError) as exc:
                transient = isinstance(
                    exc,
                    (
                        httpx.ConnectError,
                        httpx.ReadError,
                        httpx.TimeoutException,
                    ),
                )
                if isinstance(exc, HfHubHTTPError):
                    transient = (
                        exc.response.status_code == 429
                        or exc.response.status_code >= 500
                    )
                if not transient or attempt >= settings.download_max_retries:
                    raise
                sleep(settings.retry_base_delay_seconds * 2**attempt)
    except MemoryError:
        raise
    except RerankerError:
        raise
    except Exception as exc:
        raise RerankerUnavailableError(
            "The pinned reranker snapshot is unavailable."
        ) from exc
    raise RerankerUnavailableError("The pinned reranker snapshot is unavailable.")


class PassageOnlyTokenizer:
    """Make CrossEncoder.predict's truncation explicit and passage-only."""

    def __init__(self, tokenizer: Any, max_length: int) -> None:
        self._tokenizer = tokenizer
        self.model_max_length = max_length

    def __getattr__(self, name: str) -> Any:
        return getattr(self._tokenizer, name)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        if kwargs.get("truncation"):
            kwargs.update(truncation="only_second", max_length=self.model_max_length)
        return self._tokenizer(*args, **kwargs)


def load_reranker_model(
    path: Path, settings: RerankerSettings
) -> CrossEncoderModel:
    """Load safetensors locally; use Identity to preserve the raw logit."""
    try:
        from sentence_transformers import CrossEncoder
        from torch.nn import Identity

        model = CrossEncoder(
            str(path),
            device="cpu",
            max_length=settings.max_length,
            activation_fn=Identity(),
            trust_remote_code=False,
            local_files_only=True,
            token=False,
            model_kwargs={"use_safetensors": True},
        )
        if model.config.num_labels != 1:
            raise RerankerUnavailableError(
                "The reranker must return one logit per pair."
            )
        model.tokenizer = PassageOnlyTokenizer(model.tokenizer, settings.max_length)
        return model
    except MemoryError:
        raise
    except RerankerError:
        raise
    except Exception as exc:
        raise RerankerUnavailableError("The local reranker could not be loaded.") from exc


def rank_candidates(
    candidates: Sequence[HybridRetrievedChunk],
    scores: Sequence[float],
    *,
    truncated_candidate_count: int = 0,
    model_load_seconds: float = 0.0,
    inference_seconds: float = 0.0,
) -> RerankOutcome:
    """Bind scores by position, sort deterministically, and trace every candidate."""
    if len(candidates) > HYBRID_CANDIDATE_K or len(scores) != len(candidates):
        raise RerankerResultError("The reranker returned an invalid score count.")
    if len({item.chunk_id for item in candidates}) != len(candidates):
        raise HybridResultError("Hybrid returned duplicate Chunk identities.")
    validated: list[tuple[HybridRetrievedChunk, int, float]] = []
    for rank, (item, value) in enumerate(
        zip(candidates, scores, strict=True), start=1
    ):
        if (
            isinstance(value, bool)
            or not isinstance(value, Real)
            or not math.isfinite(value)
        ):
            raise RerankerResultError(
                "The reranker returned a non-finite or invalid score."
            )
        if item.vector_score is not None and (
            isinstance(item.vector_score, bool)
            or not isinstance(item.vector_score, Real)
            or not math.isfinite(item.vector_score)
        ):
            raise HybridResultError("Hybrid returned invalid vector evidence.")
        validated.append((item, rank, float(value)))
    validated.sort(
        key=lambda row: (
            -row[2], row[1], str(row[0].doc_id),
            row[0].chunk_index, str(row[0].chunk_id),
        )
    )
    ranked = tuple(
        RerankedChunk(
            chunk_id=item.chunk_id,
            doc_id=item.doc_id,
            chunk_index=item.chunk_index,
            content=item.content,
            page=item.page,
            filename=item.filename,
            metadata=dict(item.metadata),
            score=score,
            hybrid_score=item.score,
            hybrid_rank=before,
            rerank_rank=after,
            rank_change=before-after,
            vector_score=item.vector_score,
            vector_rank=item.vector_rank,
            bm25_rank=item.bm25_rank,
        )
        for after, (item, before, score) in enumerate(validated, start=1)
    )
    movements = tuple(
        RankMovement(
            str(item.chunk_id), str(item.doc_id), item.hybrid_rank,
            item.rerank_rank, item.rank_change, item.score,
        )
        for item in ranked
    )
    return RerankOutcome(
        ranked[:RERANK_FINAL_K], movements, len(candidates),
        truncated_candidate_count, model_load_seconds, inference_seconds,
    )


class RerankerService:
    """Lazy CPU model adapter, injected in ordinary tests."""

    def __init__(
        self,
        settings: RerankerSettings,
        *,
        snapshot_resolver: Callable[
            [RerankerSettings], Path
        ] = ensure_reranker_snapshot,
        model_loader: Callable[
            [Path, RerankerSettings], CrossEncoderModel
        ] = load_reranker_model,
    ) -> None:
        self.settings = settings
        self._snapshot_resolver = snapshot_resolver
        self._model_loader = model_loader
        self._model: CrossEncoderModel | None = None
        self._lock = Lock()

    def rerank(
        self, query: str, candidates: Sequence[HybridRetrievedChunk]
    ) -> RerankOutcome:
        """Score every candidate, preserving the complete query and all identities."""
        query = _validated_query(query)
        # Validate identities and count before any download or inference.
        rank_candidates(candidates, [0.0] * len(candidates))
        if not candidates:
            return rank_candidates([], [])
        with self._lock:
            started = time.perf_counter()
            loaded = self._model is None
            if self._model is None:
                try:
                    self._model = self._model_loader(
                        self._snapshot_resolver(self.settings), self.settings
                    )
                except MemoryError:
                    raise
                except RerankerError:
                    raise
                except Exception as exc:
                    raise RerankerUnavailableError(
                        "The local reranker could not be loaded."
                    ) from exc
            load_seconds = time.perf_counter() - started if loaded else 0.0
            model = self._model
            pairs = [(query, candidate.content) for candidate in candidates]
            try:
                query_ids = model.tokenizer.encode(
                    query, add_special_tokens=False, truncation=False
                )
                special_count = model.tokenizer.num_special_tokens_to_add(pair=True)
                if len(query_ids) + special_count >= self.settings.max_length:
                    raise RerankerInputError("The query exceeds the reranker input limit.")
                encoded = model.tokenizer(
                    pairs, truncation=False, padding=False,
                    add_special_tokens=True,
                )
                lengths = [len(ids) for ids in encoded["input_ids"]]
                if len(lengths) != len(candidates):
                    raise RerankerResultError(
                        "The reranker tokenizer returned an invalid count."
                    )
                truncated = sum(length > self.settings.max_length for length in lengths)
                from torch.nn import Identity

                started = time.perf_counter()
                raw = model.predict(
                    pairs,
                    batch_size=self.settings.batch_size,
                    show_progress_bar=False,
                    activation_fn=Identity(),
                    apply_softmax=False,
                    convert_to_numpy=True,
                    convert_to_tensor=False,
                )
                inference_seconds = time.perf_counter() - started
                scores = raw.tolist() if hasattr(raw, "tolist") else raw
                if not isinstance(scores, (list, tuple)):
                    raise RerankerResultError(
                        "The reranker returned an invalid score array."
                    )
            except MemoryError:
                raise
            except RerankerError:
                raise
            except Exception as exc:
                raise RerankerUnavailableError(
                    "The local reranker inference failed."
                ) from exc
        return rank_candidates(
            candidates, scores,
            truncated_candidate_count=truncated,
            model_load_seconds=load_seconds,
            inference_seconds=inference_seconds,
        )


def _validated_query(query: str) -> str:
    if not isinstance(query, str) or not 1 <= len(query.strip()) <= 4096:
        raise RerankerInputError("The query must contain 1 to 4096 characters.")
    return query.strip()


class RerankedRetrievalService:
    """The fixed Day 12 retrieval pipeline used by both API and chat."""

    def __init__(
        self, hybrid_service: HybridRetrievalService, reranker: RerankerService
    ) -> None:
        self._hybrid_service = hybrid_service
        self._reranker = reranker

    def search(self, query: str, *, doc_id: UUID | None = None) -> RerankOutcome:
        """Retrieve 20, rerank all candidates, and record complete rank movement."""
        query = _validated_query(query)
        if doc_id is not None and not isinstance(doc_id, UUID):
            raise RerankerInputError("doc_id must be a UUID or None.")
        candidates = self._hybrid_service.search(
            query, top_k=HYBRID_CANDIDATE_K, doc_id=doc_id
        )
        if doc_id is not None and any(item.doc_id != doc_id for item in candidates):
            raise HybridResultError(
                "Hybrid returned a result outside the requested document."
            )
        outcome = self._reranker.rerank(query, candidates)
        event = dict(
            event=RERANK_SEARCH_EVENT,
            query_sha256=hashlib.sha256(query.encode("utf-8")).hexdigest(),
            query_len=len(query),
            candidate_k=HYBRID_CANDIDATE_K,
            final_k=RERANK_FINAL_K,
            filter_doc_id=None if doc_id is None else str(doc_id),
            candidate_count=outcome.candidate_count,
            result_count=len(outcome.results),
            truncated_candidate_count=outcome.truncated_candidate_count,
            model_load_seconds=outcome.model_load_seconds,
            inference_seconds=outcome.inference_seconds,
            movements=[asdict(item) for item in outcome.movements],
        )
        try:
            message = json.dumps(
                event, ensure_ascii=False, separators=(",", ":"), allow_nan=False
            )
        except (TypeError, ValueError):
            logger.error("Rerank search event serialization failed.")
        else:
            logger.bind(**{JSONL_LOG_MARKER: True}).info(message)
        return outcome


@lru_cache
def get_reranked_retrieval_service() -> RerankedRetrievalService:
    """Create lazy dependencies without model loading or database access."""
    return RerankedRetrievalService(
        get_hybrid_retrieval_service(), RerankerService(get_reranker_settings())
    )
