"""Values shared by the Streamlit UI and its backend client."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

TOOL_LABELS = {
    "search_knowledge_base": "搜索知识库",
    "list_documents": "列出文档",
    "get_document_detail": "读取文档详情",
}


@dataclass(frozen=True, slots=True)
class DocumentItem:
    id: UUID
    filename: str
    size: int
    status: str
    created_at: datetime

    @classmethod
    def from_json(cls, value: object) -> "DocumentItem":
        if not isinstance(value, dict):
            raise ValueError("Invalid document")
        filename, size, created_at = value["filename"], value["size"], value["created_at"]
        if (
            not isinstance(filename, str) or not filename
            or type(size) is not int or size < 0
            or value["status"] != "ready" or not isinstance(created_at, str)
        ):
            raise ValueError("Invalid document metadata")
        return cls(UUID(str(value["id"])), filename, size, value["status"], datetime.fromisoformat(created_at))


@dataclass(frozen=True, slots=True)
class DocumentList:
    documents: tuple[DocumentItem, ...]
    truncated: bool


@dataclass(frozen=True, slots=True)
class SourceRef:
    filename: str
    page: int

    @classmethod
    def from_json(cls, value: object) -> "SourceRef":
        if not isinstance(value, dict):
            raise ValueError("Invalid source")
        filename, page = value.get("filename"), value.get("page")
        if not isinstance(filename, str) or not filename or type(page) is not int or page < 1:
            raise ValueError("Invalid source metadata")
        return cls(filename, page)


@dataclass(frozen=True, slots=True)
class ChatCompletion:
    session_id: UUID
    sources: tuple[SourceRef, ...]
    tool_name: str | None


@dataclass(slots=True)
class ChatTurn:
    question: str
    id: UUID = field(default_factory=uuid4)
    answer: str = ""
    sources: tuple[SourceRef, ...] = ()
    tool_name: str | None = None
    status: Literal["streaming", "complete", "interrupted", "error"] = "streaming"
    error: str = ""


@dataclass(slots=True)
class UiSession:
    session_id: UUID | None = None
    turns: list[ChatTurn] = field(default_factory=list)
    catalog: DocumentList | None = None
    catalog_unavailable: bool = False
    uploaded: DocumentItem | None = None
    upload_error: str = ""
    uploader_version: int = 0
