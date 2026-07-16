"""Pinned local BGE document embeddings with safe validation and batching."""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from functools import lru_cache
from numbers import Real
from pathlib import Path
from threading import Lock
from typing import Any, Protocol, cast
from uuid import UUID

import httpx
from huggingface_hub import snapshot_download
from huggingface_hub.errors import HfHubHTTPError, LocalEntryNotFoundError
from loguru import logger

from backend.app.core.config import EmbeddingSettings, get_embedding_settings


class EmbeddingError(RuntimeError):
    """Base class for safe local embedding failures."""


class ModelDownloadError(EmbeddingError):
    """Raised when the pinned model snapshot cannot be obtained safely."""


class ModelLoadError(EmbeddingError):
    """Raised when the pinned local model cannot be loaded or validated."""


class EmbeddingInputError(EmbeddingError):
    """Raised when document text is not safe to encode."""


class EmbeddingInputTooLongError(EmbeddingInputError):
    """Raised before inference when BGE would otherwise truncate an input."""

    def __init__(
        self,
        *,
        token_count: int,
        max_tokens: int,
        input_index: int | None = None,
    ) -> None:
        self.token_count = token_count
        self.max_tokens = max_tokens
        self.input_index = input_index
        prefix = "" if input_index is None else f"input_index={input_index} "
        super().__init__(
            f"{prefix}bge_token_count={token_count} model_max_tokens={max_tokens}"
        )


class ChunkEmbeddingInputTooLongError(EmbeddingInputError):
    """Expose only safe Chunk identity and length details to callers."""

    def __init__(self, chunk_id: UUID, *, token_count: int, max_tokens: int) -> None:
        self.chunk_id = chunk_id
        self.token_count = token_count
        self.max_tokens = max_tokens
        super().__init__(
            f"chunk_id={chunk_id} bge_token_count={token_count} "
            f"model_max_tokens={max_tokens}"
        )


class EmbeddingResultError(EmbeddingError):
    """Raised when local inference returns an invalid vector result."""


@dataclass(frozen=True, slots=True)
class ChunkEmbeddingInput:
    """Minimal Chunk data accepted by the Day 6 embedding boundary."""

    chunk_id: UUID
    content: str


@dataclass(frozen=True, slots=True)
class EmbeddedChunk:
    """A Chunk identity bound to one validated in-memory vector."""

    chunk_id: UUID
    vector: tuple[float, ...]


class Tokenizer(Protocol):
    """Tokenizer surface required for pre-inference length validation."""

    def encode(
        self,
        text: str,
        *,
        add_special_tokens: bool,
        truncation: bool,
    ) -> Sequence[int]: ...


class SentenceEmbeddingModel(Protocol):
    """SentenceTransformers surface used without importing it at module load."""

    tokenizer: Tokenizer
    max_seq_length: int

    def encode(self, sentences: list[str], **kwargs: Any) -> Any: ...

    def get_sentence_embedding_dimension(self) -> int | None: ...


SnapshotDownloader = Callable[..., str | list[Any]]
SnapshotResolver = Callable[[EmbeddingSettings], Path]
ModelLoader = Callable[[Path, EmbeddingSettings], SentenceEmbeddingModel]


def ensure_model_snapshot(
    settings: EmbeddingSettings,
    *,
    downloader: SnapshotDownloader = snapshot_download,
    sleep: Callable[[float], None] = time.sleep,
) -> Path:
    """Return the pinned snapshot, retrying only transient download failures."""
    try:
        settings.cache_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ModelDownloadError(
            "The embedding model cache directory is unavailable."
        ) from exc
    common_arguments = {
        "repo_id": settings.model_name,
        "revision": settings.model_revision,
        "cache_dir": settings.cache_dir,
        "token": False,
    }

    try:
        cached = downloader(**common_arguments, local_files_only=True)
    except LocalEntryNotFoundError:
        pass
    except MemoryError:
        raise
    except Exception as exc:
        raise ModelDownloadError(
            "The cached embedding model snapshot is invalid."
        ) from exc
    else:
        return _validated_snapshot_path(cached)

    for retry_index in range(settings.download_max_retries + 1):
        try:
            downloaded = downloader(**common_arguments, local_files_only=False)
            return _validated_snapshot_path(downloaded)
        except MemoryError:
            raise
        except Exception as exc:
            can_retry = _is_retryable_download_error(exc)
            retries_exhausted = retry_index >= settings.download_max_retries
            if not can_retry or retries_exhausted:
                raise ModelDownloadError(
                    "The pinned embedding model snapshot is unavailable."
                ) from exc

            delay = settings.retry_base_delay_seconds * (2**retry_index)
            logger.warning(
                "Embedding model download failed with {}; retrying in {:.2f}s",
                type(exc).__name__,
                delay,
            )
            sleep(delay)

    raise AssertionError("unreachable model download state")


def load_embedding_model(
    model_path: Path,
    settings: EmbeddingSettings,
) -> SentenceEmbeddingModel:
    """Load the pinned snapshot locally and reuse one process-wide model."""
    return _load_embedding_model_cached(
        model_path.resolve(),
        settings.device,
        settings.cache_dir.resolve(),
        settings.dimension,
    )


@lru_cache(maxsize=1)
def _load_embedding_model_cached(
    model_path: Path,
    device: str,
    cache_dir: Path,
    expected_dimension: int,
) -> SentenceEmbeddingModel:
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(
            str(model_path),
            device=device,
            cache_folder=str(cache_dir),
            trust_remote_code=False,
            local_files_only=True,
            token=False,
        )
    except MemoryError:
        raise
    except Exception as exc:
        raise ModelLoadError("The local embedding model could not be loaded.") from exc

    typed_model = cast(SentenceEmbeddingModel, model)
    dimension = typed_model.get_sentence_embedding_dimension()
    if dimension != expected_dimension:
        raise ModelLoadError(
            "The local embedding model has an unexpected vector dimension."
        )
    _model_max_tokens(typed_model)
    return typed_model


def validate_model_input_length(
    model: SentenceEmbeddingModel,
    text: str,
) -> int:
    """Count BGE tokens including special tokens and reject truncation."""
    if not isinstance(text, str) or not text.strip():
        raise EmbeddingInputError("Embedding input must not be blank.")

    try:
        token_ids = model.tokenizer.encode(
            text,
            add_special_tokens=True,
            truncation=False,
        )
    except MemoryError:
        raise
    except Exception as exc:
        raise EmbeddingInputError("Embedding input tokenization failed.") from exc

    token_count = len(token_ids)
    max_tokens = _model_max_tokens(model)
    if token_count > max_tokens:
        raise EmbeddingInputTooLongError(
            token_count=token_count,
            max_tokens=max_tokens,
        )
    return token_count


class EmbeddingClient:
    """Lazy local BGE client for validated document-passage embeddings."""

    def __init__(
        self,
        settings: EmbeddingSettings,
        *,
        snapshot_resolver: SnapshotResolver = ensure_model_snapshot,
        model_loader: ModelLoader = load_embedding_model,
    ) -> None:
        self.settings = settings
        self._snapshot_resolver = snapshot_resolver
        self._model_loader = model_loader
        self._model: SentenceEmbeddingModel | None = None
        self._model_lock = Lock()

    @property
    def dimension(self) -> int:
        """Return the fixed vector dimension without loading the model."""
        return self.settings.dimension

    def embed_documents(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        """Embed passages in order, using bounded batches and no query prompt."""
        if isinstance(texts, (str, bytes)):
            raise EmbeddingInputError("Embedding inputs must be a sequence of text.")
        if not texts:
            return []

        normalized_texts = list(texts)
        for input_index, text in enumerate(normalized_texts):
            if not isinstance(text, str) or not text.strip():
                raise EmbeddingInputError(
                    f"input_index={input_index} embedding input must not be blank"
                )

        model = self._get_model()
        for input_index, text in enumerate(normalized_texts):
            try:
                validate_model_input_length(model, text)
            except EmbeddingInputTooLongError as exc:
                raise EmbeddingInputTooLongError(
                    input_index=input_index,
                    token_count=exc.token_count,
                    max_tokens=exc.max_tokens,
                ) from exc

        vectors: list[tuple[float, ...]] = []
        for start in range(0, len(normalized_texts), self.settings.batch_size):
            batch = normalized_texts[start : start + self.settings.batch_size]
            try:
                raw_vectors = model.encode(
                    batch,
                    batch_size=self.settings.batch_size,
                    show_progress_bar=False,
                    convert_to_numpy=True,
                    convert_to_tensor=False,
                    device=self.settings.device,
                    normalize_embeddings=self.settings.normalize_embeddings,
                )
            except MemoryError:
                raise
            except Exception as exc:
                raise EmbeddingError("Local embedding inference failed.") from exc

            batch_vectors = _coerce_vector_rows(raw_vectors)
            if len(batch_vectors) != len(batch):
                raise EmbeddingResultError(
                    "Embedding result count does not match the input count."
                )
            vectors.extend(
                _validate_vector(
                    vector,
                    dimension=self.settings.dimension,
                    input_index=start + offset,
                )
                for offset, vector in enumerate(batch_vectors)
            )

        if len(vectors) != len(normalized_texts):
            raise EmbeddingResultError(
                "Embedding result count does not match the input count."
            )
        return vectors

    def _get_model(self) -> SentenceEmbeddingModel:
        if self._model is not None:
            return self._model
        with self._model_lock:
            if self._model is None:
                model_path = self._snapshot_resolver(self.settings)
                self._model = self._model_loader(model_path, self.settings)
        return self._model


def embed_chunks(
    chunks: Sequence[ChunkEmbeddingInput],
    client: EmbeddingClient,
) -> list[EmbeddedChunk]:
    """Embed Chunk content and bind each validated vector back by position."""
    if not chunks:
        return []

    validated_chunks = list(chunks)
    seen_ids: set[UUID] = set()
    for chunk in validated_chunks:
        if not isinstance(chunk.chunk_id, UUID):
            raise EmbeddingInputError("chunk_id must be a UUID")
        if chunk.chunk_id in seen_ids:
            raise EmbeddingInputError("chunk_id values must be unique")
        if not isinstance(chunk.content, str) or not chunk.content.strip():
            raise EmbeddingInputError(
                f"chunk_id={chunk.chunk_id} embedding input must not be blank"
            )
        seen_ids.add(chunk.chunk_id)

    try:
        vectors = client.embed_documents(
            [chunk.content for chunk in validated_chunks]
        )
    except EmbeddingInputTooLongError as exc:
        if exc.input_index is None or exc.input_index >= len(validated_chunks):
            raise
        chunk = validated_chunks[exc.input_index]
        raise ChunkEmbeddingInputTooLongError(
            chunk.chunk_id,
            token_count=exc.token_count,
            max_tokens=exc.max_tokens,
        ) from exc

    if len(vectors) != len(validated_chunks):
        raise EmbeddingResultError(
            "Embedding result count does not match the Chunk count."
        )

    embedded: list[EmbeddedChunk] = []
    for input_index, (chunk, vector) in enumerate(
        zip(validated_chunks, vectors, strict=True)
    ):
        embedded.append(
            EmbeddedChunk(
                chunk_id=chunk.chunk_id,
                vector=_validate_vector(
                    vector,
                    dimension=client.dimension,
                    input_index=input_index,
                ),
            )
        )
    return embedded


@lru_cache
def get_embedding_client() -> EmbeddingClient:
    """Return one lazy process-wide client for the pinned local model."""
    return EmbeddingClient(get_embedding_settings())


def _validated_snapshot_path(value: str | list[Any]) -> Path:
    if not isinstance(value, str):
        raise ModelDownloadError("The model snapshot download returned no path.")
    path = Path(value).resolve()
    if not path.is_dir():
        raise ModelDownloadError("The model snapshot path is invalid.")
    return path


def _is_retryable_download_error(exc: BaseException) -> bool:
    current: BaseException | None = exc
    visited: set[int] = set()
    while current is not None and id(current) not in visited:
        visited.add(id(current))
        if isinstance(
            current,
            (TimeoutError, ConnectionError, httpx.TimeoutException, httpx.NetworkError),
        ):
            return True
        if isinstance(current, HfHubHTTPError):
            status_code = getattr(current.response, "status_code", None)
            return status_code == 429 or (
                isinstance(status_code, int) and status_code >= 500
            )
        current = current.__cause__ or current.__context__
    return False


def _model_max_tokens(model: SentenceEmbeddingModel) -> int:
    max_tokens = getattr(model, "max_seq_length", None)
    if not isinstance(max_tokens, int) or isinstance(max_tokens, bool) or max_tokens <= 0:
        raise ModelLoadError("The local embedding model has no safe token limit.")
    return max_tokens


def _coerce_vector_rows(raw_vectors: Any) -> list[Iterable[Real]]:
    try:
        rows = list(raw_vectors)
    except TypeError as exc:
        raise EmbeddingResultError("Embedding inference returned invalid output.") from exc
    return cast(list[Iterable[Real]], rows)


def _validate_vector(
    vector: Iterable[Real],
    *,
    dimension: int,
    input_index: int,
) -> tuple[float, ...]:
    try:
        values = list(vector)
    except TypeError as exc:
        raise EmbeddingResultError(
            f"input_index={input_index} embedding vector is invalid"
        ) from exc

    if len(values) != dimension:
        raise EmbeddingResultError(
            f"input_index={input_index} embedding dimension must be {dimension}"
        )

    converted: list[float] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, Real):
            raise EmbeddingResultError(
                f"input_index={input_index} embedding vector is not numeric"
            )
        converted_value = float(value)
        if not math.isfinite(converted_value):
            raise EmbeddingResultError(
                f"input_index={input_index} embedding vector is not finite"
            )
        converted.append(converted_value)

    norm = math.sqrt(sum(value * value for value in converted))
    if not math.isclose(norm, 1.0, rel_tol=1e-4, abs_tol=1e-4):
        raise EmbeddingResultError(
            f"input_index={input_index} embedding vector is not normalized"
        )
    return tuple(converted)
