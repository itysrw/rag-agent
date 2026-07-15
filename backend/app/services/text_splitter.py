"""Pure, page-aware token chunking for newly uploaded documents."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import tiktoken
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.app.services.document_parser import PageText

JSONScalar = str | int | float | bool | None

CHUNK_SEPARATORS = [
    "\n\n",
    "\n",
    "。",
    "！",
    "？",
    ".",
    "!",
    "?",
    "；",
    ";",
    "，",
    ",",
    " ",
]


@dataclass(frozen=True, slots=True)
class ChunkDraft:
    """One ordered chunk ready to be associated with a document row."""

    chunk_index: int
    content: str
    page: int
    metadata: dict[str, JSONScalar]


class TextSplittingError(RuntimeError):
    """Raised when token chunking cannot produce safe, bounded chunks."""


def split_pages(
    pages: Sequence[PageText],
    *,
    chunk_size: int,
    chunk_overlap: int,
    encoding_name: str,
) -> list[ChunkDraft]:
    """Split each nonblank page independently into deterministic token chunks."""
    normalized_encoding_name = encoding_name.strip()
    _validate_configuration(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        encoding_name=normalized_encoding_name,
    )

    try:
        encoding = tiktoken.get_encoding(normalized_encoding_name)
    except MemoryError:
        raise
    except Exception as exc:
        raise TextSplittingError("The tokenizer encoding is not available") from exc

    def token_length(text: str) -> int:
        return len(encoding.encode(text, disallowed_special=()))

    try:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=token_length,
            separators=CHUNK_SEPARATORS,
            keep_separator="end",
        )
        drafts: list[ChunkDraft] = []
        for page in pages:
            if page.page < 1:
                raise TextSplittingError("Source pages must use one-based numbering")
            if not page.text.strip():
                continue

            for content in splitter.split_text(page.text):
                for bounded_content, token_count in _split_by_token_windows(
                    content,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    token_length=token_length,
                ):
                    if not bounded_content.strip():
                        continue
                    drafts.append(
                        ChunkDraft(
                            chunk_index=len(drafts),
                            content=bounded_content,
                            page=page.page,
                            metadata={
                                "chunk_size": chunk_size,
                                "chunk_overlap": chunk_overlap,
                                "length_unit": "token",
                                "encoding_name": normalized_encoding_name,
                                "token_count": token_count,
                            },
                        )
                    )
    except TextSplittingError:
        raise
    except Exception as exc:
        raise TextSplittingError("The document could not be split into chunks") from exc

    if not drafts:
        raise TextSplittingError("The document produced no nonblank chunks")
    return drafts


def _split_by_token_windows(
    text: str,
    *,
    chunk_size: int,
    chunk_overlap: int,
    token_length: Callable[[str], int],
) -> list[tuple[str, int]]:
    token_count = token_length(text)
    if token_count <= chunk_size:
        return [(text, token_count)]

    chunks: list[tuple[str, int]] = []
    start = 0
    while start < len(text):
        end, token_count = _find_chunk_end(
            text,
            start=start,
            chunk_size=chunk_size,
            token_length=token_length,
        )
        if end <= start:
            raise TextSplittingError(
                "A source character exceeds the configured token limit"
            )

        chunks.append((text[start:end], token_count))
        if end == len(text):
            break

        next_start = _find_overlap_start(
            text,
            start=start,
            end=end,
            token_count=token_count,
            chunk_overlap=chunk_overlap,
            token_length=token_length,
        )
        if next_start <= start:
            raise TextSplittingError("Token chunking did not make forward progress")
        start = next_start

    return chunks


def _find_chunk_end(
    text: str,
    *,
    start: int,
    chunk_size: int,
    token_length: Callable[[str], int],
) -> tuple[int, int]:
    text_end = len(text)
    candidate = min(text_end, start + chunk_size)
    candidate_count = token_length(text[start:candidate])
    best_end = start
    best_count = 0

    if candidate_count <= chunk_size:
        best_end = candidate
        best_count = candidate_count
        if candidate_count == chunk_size or candidate == text_end:
            return best_end, best_count

        while candidate < text_end:
            span = candidate - start
            candidate = min(text_end, start + span * 2)
            candidate_count = token_length(text[start:candidate])
            if candidate_count <= chunk_size:
                best_end = candidate
                best_count = candidate_count
                if candidate_count == chunk_size or candidate == text_end:
                    return best_end, best_count
                continue
            break

    low = best_end + 1
    high = candidate - 1
    while low <= high:
        midpoint = (low + high) // 2
        midpoint_count = token_length(text[start:midpoint])
        if midpoint_count <= chunk_size:
            best_end = midpoint
            best_count = midpoint_count
            low = midpoint + 1
        else:
            high = midpoint - 1

    return best_end, best_count


def _find_overlap_start(
    text: str,
    *,
    start: int,
    end: int,
    token_count: int,
    chunk_overlap: int,
    token_length: Callable[[str], int],
) -> int:
    if chunk_overlap == 0:
        return end

    span = end - start
    overlap_characters = max(1, span * chunk_overlap // token_count)
    candidate = max(start + 1, end - overlap_characters)
    candidate_count = token_length(text[candidate:end])
    if candidate_count == chunk_overlap:
        return candidate

    if candidate_count < chunk_overlap:
        low = start + 1
        high = candidate - 1
        best_start = candidate
    else:
        low = candidate + 1
        high = end
        best_start = end

    while low <= high:
        midpoint = (low + high) // 2
        midpoint_count = token_length(text[midpoint:end])
        if midpoint_count <= chunk_overlap:
            best_start = midpoint
            high = midpoint - 1
        else:
            low = midpoint + 1

    return best_start


def _validate_configuration(
    *,
    chunk_size: int,
    chunk_overlap: int,
    encoding_name: str,
) -> None:
    if chunk_size <= 0:
        raise TextSplittingError("chunk_size must be positive")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise TextSplittingError(
            "chunk_overlap must be nonnegative and smaller than chunk_size"
        )
    if not encoding_name:
        raise TextSplittingError("encoding_name must not be empty")
