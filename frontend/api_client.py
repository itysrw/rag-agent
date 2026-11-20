"""Server-side HTTP client for the public RAG endpoints."""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO
from uuid import UUID

import httpx

from backend.app.document_formats import UPLOAD_CONTENT_TYPES
from frontend.models import TOOL_LABELS, ChatCompletion, DocumentItem, DocumentList
from frontend.sse import StreamError, StreamInterrupted, read_chat_events

DEFAULT_BACKEND_URL = "http://127.0.0.1:8000"
_TIMEOUT = httpx.Timeout(180.0, connect=5.0, write=30.0, pool=5.0)


_UPLOAD_TYPE_ERROR = "文件类型不受支持，请选择 .pdf、.md 或 .txt。"


class ApiError(RuntimeError):
    """A safe status message for the UI, with no response body attached."""


def _check_status(response: httpx.Response, expected: int, operation: str) -> None:
    code = response.status_code
    if code == expected:
        return
    if operation == "上传":
        upload_errors = {
            400: "文件为空、损坏，或内容无法解析（文本须使用 UTF-8）。",
            413: "文件超过后端允许的大小。",
            415: _UPLOAD_TYPE_ERROR,
        }
        if code in upload_errors:
            raise ApiError(upload_errors[code])
    if operation == "问答":
        chat_errors = {
            404: "会话已不可用，请新建对话。",
            409: "此会话已有请求在处理。",
            422: "问题格式不合规或超过模型输入长度。",
        }
        if code in chat_errors:
            raise ApiError(chat_errors[code])
    raise ApiError(f"{operation}失败（HTTP {code}）。")


class RagClient:
    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def list_documents(self) -> DocumentList:
        try:
            response = self._client.get("/documents")
            _check_status(response, 200, "读取文档列表")
            payload = response.json()
            if not isinstance(payload, dict) or type(payload.get("truncated")) is not bool:
                raise ValueError("Invalid catalog")
            rows = payload.get("documents")
            if not isinstance(rows, list):
                raise ValueError("Invalid catalog items")
            return DocumentList(tuple(DocumentItem.from_json(row) for row in rows), payload["truncated"])
        except httpx.RequestError as exc:
            raise ApiError("文档列表暂时无法连接，请手动刷新。") from exc
        except (TypeError, ValueError, KeyError) as exc:
            raise ApiError("后端返回了无效的文档列表。") from exc

    def upload_document(self, filename: str, file: BinaryIO) -> DocumentItem:
        content_types = UPLOAD_CONTENT_TYPES.get(Path(filename.strip()).suffix.lower())
        if content_types is None:
            raise ApiError(_UPLOAD_TYPE_ERROR)
        content_type = content_types[0]
        try:
            response = self._client.post("/documents/upload", files={"file": (filename, file, content_type)})
            _check_status(response, 201, "上传")
            return DocumentItem.from_json(response.json())
        except httpx.RequestError as exc:
            raise ApiError("未收到上传确认。后端可能已保存文件，请先刷新文档列表。") from exc
        except (TypeError, ValueError, KeyError) as exc:
            raise ApiError("上传返回 201，但文档信息无效，请刷新列表查看。") from exc

    def stream_chat(self, message: str, session_id: UUID | None) -> Iterator[str | ChatCompletion]:
        payload = {"message": message, "stream": True}
        if session_id is not None:
            payload["session_id"] = str(session_id)
        try:
            with self._client.stream(
                "POST", "/chat", json=payload, headers={"Accept": "text/event-stream"},
            ) as response:
                _check_status(response, 200, "问答")
                if response.headers.get("content-type", "").split(";", 1)[0].lower().strip() != "text/event-stream":
                    raise StreamError("后端返回了无效的聊天流。")
                response.encoding = "utf-8"
                try:
                    returned_id = UUID(response.headers["X-Session-ID"])
                except (ValueError, KeyError) as exc:
                    raise StreamError("后端未返回有效的会话 ID。") from exc
                if session_id is not None and returned_id != session_id:
                    raise StreamError("返回的会话与当前对话不一致。")
                tool = response.headers.get("X-Agent-Tool")
                for event in read_chat_events(response.iter_text()):
                    if isinstance(event, str):
                        yield event
                    else:
                        yield ChatCompletion(returned_id, event, tool if tool in TOOL_LABELS else None)
        except httpx.ConnectError as exc:
            raise ApiError("无法连接问答后端。") from exc
        except httpx.TimeoutException as exc:
            raise StreamInterrupted("问答请求超时，后端可能已保存本轮。") from exc
        except httpx.RequestError as exc:
            raise StreamInterrupted("问答连接中断，后端可能已保存本轮。") from exc


@contextmanager
def open_client() -> Iterator[RagClient]:
    """Read the operator's backend URL once per page run."""
    base_url = os.environ.get("RAG_BACKEND_URL", DEFAULT_BACKEND_URL)
    with httpx.Client(base_url=base_url, timeout=_TIMEOUT, trust_env=False) as client:
        yield RagClient(client)
