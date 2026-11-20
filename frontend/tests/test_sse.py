"""SSE framing, evidence staging, and terminal event tests."""

import pytest

from frontend.models import SourceRef
from frontend.sse import StreamError, StreamInterrupted, read_chat_events, read_events


def test_events_decode_split_crlf_comments_and_multiline_data() -> None:
    chunks = [
        "\ufeff: heartbeat\r", "\n\r\nevent: note\r\n", "data:  first\r",
        "\ndata: second\r\n", "\rid: ignored\n", "data: last\n\n",
    ]
    assert list(read_events(chunks)) == [("note", " first\nsecond"), ("message", "last")]


def test_chat_yields_deltas_before_sources_are_confirmed() -> None:
    events = read_chat_events(iter(
        'data: {"delta":"你\u2028好"}\r\n\r\n'
        'event: sources\r\ndata: {"sources":[{"filename":"手册.pdf","page":2}]}\r\n\r\n'
        'data: [DONE]\r\n\r\n'
    ))
    assert next(events) == "你\u2028好"
    assert next(events) == (SourceRef("手册.pdf", 2),)
    assert list(events) == []


def test_chat_allows_empty_sources() -> None:
    events = ["data: {\"delta\":\"没有相关知识\"}\n\n", "event: sources\n",
              "data: {\"sources\":[]}\n\n", "data: [DONE]\n\n"]
    assert list(read_chat_events(events)) == ["没有相关知识", ()]


@pytest.mark.parametrize(("tail", "error"), [
    ("", StreamInterrupted),
    ("data: [DONE]\n\n", StreamError),
    ("event: sources\ndata: {\"sources\":[]}\n\ndata: [DONE]\n", StreamInterrupted),
    ("event: error\ndata: {\"message\":\"internal body\"}\n\n", StreamError),
    ("event: sources\ndata: {\"sources\":[{\"filename\":\"p\",\"page\":true}]}\n\n", StreamError),
    ("event: sources\ndata: {\"sources\":[]}\n\ndata: {\"delta\":\"late\"}\n\n", StreamError),
])
def test_chat_rejects_unconfirmed_or_invalid_turns(tail: str, error: type[StreamError]) -> None:
    events = read_chat_events(['data: {"delta":"部分"}\n\n', tail])
    assert next(events) == "部分"
    with pytest.raises(error) as failure:
        next(events)
    assert "internal body" not in str(failure.value)
