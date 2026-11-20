"""Exercise the frontend HTTP contract without using a network or API keys."""

import json
from collections.abc import Iterator
from io import BytesIO
from uuid import UUID

import httpx
import pytest

from frontend.api_client import ApiError, RagClient
from frontend.models import ChatCompletion, SourceRef
from frontend.sse import StreamError, StreamInterrupted

SESSION_ID = UUID(int=1)
DOC_ID = UUID(int=2)
DOC = {"id": str(DOC_ID), "filename": "手册.txt", "size": 5,
       "status": "ready", "created_at": "2026-11-18T06:00:00Z"}


class ChunkedBody(httpx.SyncByteStream):
    def __init__(self, chunks: list[bytes], *, break_after: bool = False) -> None:
        self.chunks = chunks
        self.break_after = break_after
        self.read = 0
        self.closed = False

    def __iter__(self) -> Iterator[bytes]:
        for chunk in self.chunks:
            self.read += len(chunk)
            yield chunk
        if self.break_after:
            raise httpx.ReadError("private transport error")

    def close(self) -> None:
        self.closed = True


def test_catalog_and_multipart_upload_only_use_public_metadata() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            assert request.url.path == "/documents"
            return httpx.Response(200, json={"documents": [DOC], "truncated": True})
        assert request.method == "POST" and request.url.path == "/documents/upload"
        assert request.headers["content-type"].startswith("multipart/form-data;")
        assert b'name="file";' in request.content
        assert "手册.txt".encode() in request.content and b"hello" in request.content
        return httpx.Response(201, json=DOC)

    with httpx.Client(base_url="http://test", transport=httpx.MockTransport(respond)) as http:
        client = RagClient(http)
        catalog = client.list_documents()
        assert catalog.truncated and catalog.documents[0].id == DOC_ID
        assert client.upload_document("手册.txt", BytesIO(b"hello")) == catalog.documents[0]


@pytest.mark.parametrize(("status", "message"), [(400, "无法解析"), (413, "大小"), (415, "不受支持")])
def test_upload_http_errors_use_safe_distinct_messages(status: int, message: str) -> None:
    with httpx.Client(base_url="http://test", transport=httpx.MockTransport(
        lambda request: httpx.Response(status, json={"detail": "secret"}),
    )) as http:
        with pytest.raises(ApiError, match=message) as failure:
            RagClient(http).upload_document("test.pdf", BytesIO(b"test"))
    assert "secret" not in str(failure.value)


def test_chat_decodes_fragmented_utf8_without_buffering_and_closes_connection() -> None:
    first = 'data: {"delta":"第一段"}\r\n\r\n'.encode()
    rest = ('data: {"delta":"第二段"}\r\n\r\n'
            'event: sources\r\ndata: {"sources":[{"filename":"手册.txt","page":1}]}\r\n\r\n'
            'data: [DONE]\r\n\r\n').encode()
    body = ChunkedBody([bytes([byte]) for byte in first + rest])

    def respond(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST" and request.url.path == "/chat"
        assert json.loads(request.content) == {"message": "查手册", "stream": True}
        assert request.headers["accept"] == "text/event-stream"
        return httpx.Response(200, headers={
            "Content-Type": "text/event-stream", "X-Session-ID": str(SESSION_ID),
            "X-Agent-Tool": "search_knowledge_base",
        }, stream=body)

    with httpx.Client(base_url="http://test", transport=httpx.MockTransport(respond)) as http:
        events = RagClient(http).stream_chat("查手册", None)
        assert next(events) == "第一段"
        assert body.read <= len(first) and not body.closed
        assert list(events) == [
            "第二段", ChatCompletion(SESSION_ID, (SourceRef("手册.txt", 1),), "search_knowledge_base"),
        ]
    assert body.closed


def test_chat_reuses_session_and_ignores_unknown_tool() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content)["session_id"] == str(SESSION_ID)
        return httpx.Response(
            200, headers={"Content-Type": "text/event-stream; charset=UTF-8",
                          "X-Session-ID": str(SESSION_ID), "X-Agent-Tool": "unknown"},
            content=b'event: sources\ndata: {"sources":[]}\n\ndata: [DONE]\n\n',
        )

    with httpx.Client(base_url="http://test", transport=httpx.MockTransport(respond)) as http:
        assert list(RagClient(http).stream_chat("再问一次", SESSION_ID)) == [ChatCompletion(SESSION_ID, (), None)]


def test_chat_does_not_retry_an_http_error_or_timeout() -> None:
    attempts = 0

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503, json={"detail": "private failure"})
        raise httpx.ReadTimeout("private timeout", request=request)

    with httpx.Client(base_url="http://test", transport=httpx.MockTransport(respond)) as http:
        client = RagClient(http)
        with pytest.raises(ApiError, match="HTTP 503"):
            list(client.stream_chat("ask", None))
        assert attempts == 1
        with pytest.raises(StreamInterrupted, match="超时"):
            list(client.stream_chat("ask", None))
        assert attempts == 2


def test_chat_closes_interrupted_response_and_keeps_only_the_delta() -> None:
    body = ChunkedBody([b'data: {"delta":"partial"}\n\n'], break_after=True)
    with httpx.Client(base_url="http://test", transport=httpx.MockTransport(lambda request:
        httpx.Response(200, headers={"Content-Type": "text/event-stream", "X-Session-ID": str(SESSION_ID)}, stream=body)
    )) as http:
        events = RagClient(http).stream_chat("ask", None)
        assert next(events) == "partial"
        with pytest.raises(StreamInterrupted, match="中断"):
            next(events)
    assert body.closed


def test_chat_rejects_a_different_response_session() -> None:
    with httpx.Client(base_url="http://test", transport=httpx.MockTransport(lambda request:
        httpx.Response(200, headers={"Content-Type": "text/event-stream", "X-Session-ID": str(UUID(int=3))})
    )) as http:
        with pytest.raises(StreamError, match="不一致"):
            list(RagClient(http).stream_chat("ask", SESSION_ID))


@pytest.mark.parametrize(
    ("filename", "content_type"),
    [("notes.MD", b"text/markdown"), ("notes.TXT", b"text/plain"), ("guide.PDF", b"application/pdf")],
)
def test_upload_chooses_canonical_multipart_type(filename: str, content_type: bytes) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        assert f'filename="{filename}"'.encode() in request.content
        assert b"Content-Type: " + content_type + b"\r\n" in request.content
        return httpx.Response(201, json={**DOC, "filename": filename})

    with httpx.Client(base_url="http://test", transport=httpx.MockTransport(respond)) as http:
        assert RagClient(http).upload_document(filename, BytesIO(b"hello")).filename == filename


def test_upload_rejects_an_unsupported_suffix_before_posting() -> None:
    def unexpected_request(request: httpx.Request) -> httpx.Response:
        pytest.fail(f"Unexpected request: {request.method} {request.url}")

    with httpx.Client(base_url="http://test", transport=httpx.MockTransport(unexpected_request)) as http:
        with pytest.raises(ApiError, match=r"\.md"):
            RagClient(http).upload_document("notes.markdown", BytesIO(b"hello"))
