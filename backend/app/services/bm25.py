"""Lazy PostgreSQL-backed BM25 keyword retrieval for Day 10."""

from __future__ import annotations

import hashlib
import json
import math
import re
import threading
import unicodedata
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from uuid import UUID

from loguru import logger
from pydantic import ValidationError
from rank_bm25 import BM25Okapi
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.core.database import (
    DatabaseConfigurationError,
    get_session_factory,
)
from backend.app.core.logging import JSONL_LOG_MARKER
from backend.app.models.chunk import JSONScalar, Chunk
from backend.app.models.document import Document
from backend.app.services.retrieval import (
    RETRIEVAL_TOP_K,
    RETRIEVAL_TOP_K_MAX,
    RETRIEVAL_TOP_K_MIN,
)

BM25_SEARCH_EVENT = "bm25_search_completed"
_TOKEN_RUN = re.compile(
    r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+"
    r"|[a-z0-9]+(?:[-_][a-z0-9]+)*"
)
_COMPOUND_SEPARATOR = re.compile(r"[-_]+")


class BM25Error(RuntimeError):
    """Base class for safe BM25 service failures."""


class BM25UnavailableError(BM25Error):
    """Raised when the PostgreSQL corpus cannot be loaded."""


class BM25IndexError(BM25Error):
    """Raised when the corpus, index, or score result is invalid."""


@dataclass(frozen=True, slots=True)
class BM25CorpusChunk:
    """One immutable-in-snapshot PostgreSQL Chunk projection."""

    chunk_id: UUID
    doc_id: UUID
    chunk_index: int
    content: str
    page: int
    filename: str
    metadata: dict[str, JSONScalar]


@dataclass(frozen=True, slots=True)
class BM25RetrievedChunk:
    """One BM25 result with its raw finite score."""

    chunk_id: UUID
    doc_id: UUID
    chunk_index: int
    content: str
    page: int
    filename: str
    metadata: dict[str, JSONScalar]
    score: float


@dataclass(frozen=True, slots=True)
class BM25Snapshot:
    """A complete process-local corpus and index generation."""

    fingerprint: str
    chunks: tuple[BM25CorpusChunk, ...]
    tokenized_corpus: tuple[tuple[str, ...], ...]
    index: BM25Okapi | None


SessionFactory = Callable[[], Session]
CorpusLoader = Callable[[], tuple[BM25CorpusChunk, ...]]


def tokenize_bm25(text: str) -> list[str]:
    """Tokenize mixed Chinese, English, numbers, and compound identifiers."""
    if not isinstance(text, str):
        raise ValueError("BM25 input must be text")

    normalized = unicodedata.normalize("NFKC", text).casefold()
    tokens: list[str] = []
    for match in _TOKEN_RUN.finditer(normalized):
        value = match.group(0)
        if _is_chinese_run(value):
            tokens.extend(value)
            tokens.extend(value[index : index + 2] for index in range(len(value) - 1))
            continue

        tokens.append(value)
        if "-" in value or "_" in value:
            tokens.extend(
                part for part in _COMPOUND_SEPARATOR.split(value) if part
            )
    return tokens


def load_bm25_chunks(
    *,
    session_factory: SessionFactory | None = None,
) -> tuple[BM25CorpusChunk, ...]:
    """Read ready-document Chunks in deterministic order and close the Session."""
    try:
        resolved_factory = session_factory or get_session_factory()
        with resolved_factory() as session:
            rows = session.execute(
                select(Chunk, Document.filename)
                .join(Document, Chunk.doc_id == Document.id)
                .where(Document.status == "ready")
                .order_by(Chunk.doc_id, Chunk.chunk_index, Chunk.chunk_id)
            ).all()
            chunks = tuple(
                BM25CorpusChunk(
                    chunk_id=chunk.chunk_id,
                    doc_id=chunk.doc_id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    page=chunk.page,
                    filename=filename,
                    metadata=dict(chunk.chunk_metadata),
                )
                for chunk, filename in rows
            )
    except MemoryError:
        raise
    except (DatabaseConfigurationError, ValidationError, SQLAlchemyError) as exc:
        raise BM25UnavailableError(
            "The BM25 corpus database is unavailable."
        ) from exc
    except (TypeError, ValueError) as exc:
        raise BM25IndexError("The BM25 corpus contains invalid data.") from exc

    for chunk in chunks:
        _validate_corpus_chunk(chunk)
    return chunks


def build_corpus_fingerprint(chunks: Sequence[BM25CorpusChunk]) -> str:
    """Return a stable SHA-256 for every retrieval-visible corpus field."""
    records: list[dict[str, Any]] = []
    for chunk in chunks:
        _validate_corpus_chunk(chunk)
        records.append(
            {
                "chunk_id": str(chunk.chunk_id),
                "doc_id": str(chunk.doc_id),
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "page": chunk.page,
                "filename": chunk.filename,
                "metadata": chunk.metadata,
            }
        )
    try:
        serialized = json.dumps(
            records,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise BM25IndexError("The BM25 corpus cannot be fingerprinted.") from exc
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def build_bm25_snapshot(
    chunks: Sequence[BM25CorpusChunk],
    *,
    fingerprint: str | None = None,
) -> BM25Snapshot:
    """Build one complete snapshot without mutating the active service state."""
    frozen_chunks = tuple(chunks)
    resolved_fingerprint = fingerprint or build_corpus_fingerprint(frozen_chunks)
    tokenized = tuple(tuple(tokenize_bm25(chunk.content)) for chunk in frozen_chunks)
    index: BM25Okapi | None = None
    if tokenized and any(tokens for tokens in tokenized):
        try:
            index = BM25Okapi([list(tokens) for tokens in tokenized])
        except MemoryError:
            raise
        except Exception as exc:
            raise BM25IndexError("The BM25 index could not be built.") from exc
    return BM25Snapshot(
        fingerprint=resolved_fingerprint,
        chunks=frozen_chunks,
        tokenized_corpus=tokenized,
        index=index,
    )


class BM25Service:
    """Refresh and query one process-local BM25 corpus snapshot."""

    def __init__(self, corpus_loader: CorpusLoader = load_bm25_chunks) -> None:
        self._corpus_loader = corpus_loader
        self._refresh_lock = threading.Lock()
        self._snapshot: BM25Snapshot | None = None

    def search(
        self,
        query: str,
        *,
        top_k: int = RETRIEVAL_TOP_K,
        doc_id: UUID | None = None,
    ) -> list[BM25RetrievedChunk]:
        """Return keyword-overlapping Chunks ranked by raw BM25 score."""
        validated_top_k = _validated_top_k(top_k)
        if doc_id is not None and not isinstance(doc_id, UUID):
            raise ValueError("doc_id must be a UUID or None")
        if not isinstance(query, str):
            raise ValueError("query must be text")

        query_tokens = tuple(dict.fromkeys(tokenize_bm25(query)))
        if not query_tokens:
            snapshot = self._snapshot
            results: list[BM25RetrievedChunk] = []
            _log_search_event(
                query=query,
                query_token_count=0,
                top_k=validated_top_k,
                doc_id=doc_id,
                corpus_size=0 if snapshot is None else len(snapshot.chunks),
                index_rebuilt=False,
                results=results,
            )
            return results

        snapshot, index_rebuilt = self._refresh_snapshot()
        if snapshot.index is None:
            results = []
        else:
            scores = _validated_scores(
                snapshot.index,
                query_tokens,
                corpus_size=len(snapshot.chunks),
            )
            query_token_set = set(query_tokens)
            candidates: list[BM25RetrievedChunk] = []
            for chunk, document_tokens, score in zip(
                snapshot.chunks,
                snapshot.tokenized_corpus,
                scores,
                strict=True,
            ):
                if not query_token_set.intersection(document_tokens):
                    continue
                if doc_id is not None and chunk.doc_id != doc_id:
                    continue
                candidates.append(
                    BM25RetrievedChunk(
                        chunk_id=chunk.chunk_id,
                        doc_id=chunk.doc_id,
                        chunk_index=chunk.chunk_index,
                        content=chunk.content,
                        page=chunk.page,
                        filename=chunk.filename,
                        metadata=dict(chunk.metadata),
                        score=score,
                    )
                )
            candidates.sort(
                key=lambda item: (
                    -item.score,
                    str(item.doc_id),
                    item.chunk_index,
                    str(item.chunk_id),
                )
            )
            results = candidates[:validated_top_k]

        _log_search_event(
            query=query,
            query_token_count=len(query_tokens),
            top_k=validated_top_k,
            doc_id=doc_id,
            corpus_size=len(snapshot.chunks),
            index_rebuilt=index_rebuilt,
            results=results,
        )
        return results

    def _refresh_snapshot(self) -> tuple[BM25Snapshot, bool]:
        with self._refresh_lock:
            try:
                chunks = self._corpus_loader()
            except MemoryError:
                raise
            except BM25Error:
                raise
            except Exception as exc:
                raise BM25UnavailableError(
                    "The BM25 corpus database is unavailable."
                ) from exc

            fingerprint = build_corpus_fingerprint(chunks)
            if (
                self._snapshot is not None
                and self._snapshot.fingerprint == fingerprint
            ):
                return self._snapshot, False

            replacement = build_bm25_snapshot(
                chunks,
                fingerprint=fingerprint,
            )
            self._snapshot = replacement
            return replacement, True


def _is_chinese_run(value: str) -> bool:
    return bool(value) and not value[0].isascii()


def _validate_corpus_chunk(chunk: BM25CorpusChunk) -> None:
    if not isinstance(chunk.chunk_id, UUID) or not isinstance(chunk.doc_id, UUID):
        raise BM25IndexError("The BM25 corpus contains invalid identities.")
    if (
        isinstance(chunk.chunk_index, bool)
        or not isinstance(chunk.chunk_index, int)
        or chunk.chunk_index < 0
    ):
        raise BM25IndexError("The BM25 corpus contains an invalid chunk index.")
    if not isinstance(chunk.content, str) or not chunk.content.strip():
        raise BM25IndexError("The BM25 corpus contains invalid content.")
    if isinstance(chunk.page, bool) or not isinstance(chunk.page, int) or chunk.page < 1:
        raise BM25IndexError("The BM25 corpus contains an invalid page.")
    if not isinstance(chunk.filename, str) or not chunk.filename.strip():
        raise BM25IndexError("The BM25 corpus contains an invalid filename.")
    if not isinstance(chunk.metadata, dict):
        raise BM25IndexError("The BM25 corpus contains invalid metadata.")
    for key, value in chunk.metadata.items():
        if not isinstance(key, str):
            raise BM25IndexError("The BM25 corpus contains invalid metadata.")
        if value is None or isinstance(value, (str, bool, int)):
            continue
        if isinstance(value, float) and math.isfinite(value):
            continue
        raise BM25IndexError("The BM25 corpus contains invalid metadata.")


def _validated_top_k(top_k: int) -> int:
    if isinstance(top_k, bool) or not isinstance(top_k, int):
        raise ValueError("top_k must be an integer")
    if not RETRIEVAL_TOP_K_MIN <= top_k <= RETRIEVAL_TOP_K_MAX:
        raise ValueError(
            f"top_k must be between {RETRIEVAL_TOP_K_MIN} and {RETRIEVAL_TOP_K_MAX}"
        )
    return top_k


def _validated_scores(
    index: BM25Okapi,
    query_tokens: Sequence[str],
    *,
    corpus_size: int,
) -> tuple[float, ...]:
    try:
        raw_scores = index.get_scores(list(query_tokens))
    except MemoryError:
        raise
    except Exception as exc:
        raise BM25IndexError("The BM25 query could not be scored.") from exc
    if len(raw_scores) != corpus_size:
        raise BM25IndexError("The BM25 score count is invalid.")

    converted: list[float] = []
    for score in raw_scores:
        try:
            value = float(score)
        except (TypeError, ValueError, OverflowError) as exc:
            raise BM25IndexError("The BM25 score is invalid.") from exc
        if not math.isfinite(value):
            raise BM25IndexError("The BM25 score is invalid.")
        converted.append(value)
    return tuple(converted)


def _log_search_event(
    *,
    query: str,
    query_token_count: int,
    top_k: int,
    doc_id: UUID | None,
    corpus_size: int,
    index_rebuilt: bool,
    results: Sequence[BM25RetrievedChunk],
) -> None:
    event = {
        "event": BM25_SEARCH_EVENT,
        "query_sha256": hashlib.sha256(query.encode("utf-8")).hexdigest(),
        "query_len": len(query),
        "query_token_count": query_token_count,
        "top_k": top_k,
        "filter_doc_id": None if doc_id is None else str(doc_id),
        "corpus_size": corpus_size,
        "index_rebuilt": index_rebuilt,
        "result_count": len(results),
        "results": [
            {
                "rank": rank,
                "chunk_id": str(result.chunk_id),
                "doc_id": str(result.doc_id),
                "filename": result.filename,
                "page": result.page,
                "score": result.score,
            }
            for rank, result in enumerate(results, start=1)
        ],
    }
    try:
        message = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError):
        logger.error("BM25 search event serialization failed.")
        return
    logger.bind(**{JSONL_LOG_MARKER: True}).info(message)


@lru_cache
def get_bm25_service() -> BM25Service:
    """Return a lazy process-wide BM25 service without touching PostgreSQL."""
    return BM25Service()
