"""Decode SSE framing and validate the RAG chat event sequence."""

import json
import re
from collections.abc import Iterable, Iterator

from frontend.models import SourceRef

_LINE_END = re.compile(r"\r\n|\r|\n")


class StreamError(ValueError):
    """The backend rejected the turn or sent an invalid event sequence."""


class StreamInterrupted(StreamError):
    """The connection ended before the turn could be confirmed."""


def _lines(chunks: Iterable[str]) -> Iterator[str]:
    """Split only on SSE line endings, even when CRLF spans chunks."""
    parts: list[str] = []
    pending_cr = False
    for chunk in chunks:
        if not chunk:
            continue
        if pending_cr and chunk.startswith("\n"):
            chunk = chunk[1:]
        pending_cr = chunk.endswith("\r")
        start = 0
        for separator in _LINE_END.finditer(chunk):
            parts.append(chunk[start:separator.start()])
            yield "".join(parts)
            parts.clear()
            start = separator.end()
        parts.append(chunk[start:])


def read_events(chunks: Iterable[str]) -> Iterator[tuple[str, str]]:
    """Yield named data events only after a blank line has dispatched them."""
    event = "message"
    data: list[str] = []
    first_line = True
    for line in _lines(chunks):
        if first_line:
            line = line.removeprefix("\ufeff")
            first_line = False
        if not line:
            if data:
                yield event, "\n".join(data)
            event = "message"
            data.clear()
            continue
        field, _, value = line.partition(":")
        value = value.removeprefix(" ")
        if field == "event":
            event = value or "message"
        elif field == "data":
            data.append(value)


def read_chat_events(chunks: Iterable[str]) -> Iterator[str | tuple[SourceRef, ...]]:
    """Yield deltas immediately and release sources only after a valid DONE."""
    sources: tuple[SourceRef, ...] | None = None
    for event, body in read_events(chunks):
        if event == "error":
            raise StreamError("后端报告本轮回答失败。")
        if event not in {"message", "sources"}:
            continue
        if event == "message" and body == "[DONE]":
            if sources is None:
                raise StreamError("聊天流缺少本轮引用事件。")
            yield sources
            return
        try:
            payload = json.loads(body)
            if not isinstance(payload, dict) or sources is not None:
                raise ValueError("Unexpected event")
            if event == "sources":
                rows = payload.get("sources")
                if not isinstance(rows, list):
                    raise ValueError("Expected sources")
                sources = tuple(SourceRef.from_json(row) for row in rows)
            else:
                delta = payload.get("delta")
                if not isinstance(delta, str):
                    raise ValueError("Expected delta")
                yield delta
        except ValueError as exc:
            raise StreamError("聊天流格式异常，本轮未确认。") from exc
    raise StreamInterrupted("连接在本轮确认前结束，后端可能已保存本轮。")
