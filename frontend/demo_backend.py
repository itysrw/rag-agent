"""Loopback-only demo backend with synthetic answers and in-memory documents."""

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from backend.app.core.config import MAX_UPLOAD_SIZE
from backend.app.services.document_storage import (
    UnsafeFilenameError,
    UnsupportedDocumentTypeError,
    validate_upload_metadata,
)

_PAUSE_SECONDS = 1.1
_SAMPLE_NAME = "演示手册.txt"

app = FastAPI(title="Day20 RAG demo fixture")


def _document(filename: str, size: int) -> dict[str, str | int]:
    return {
        "id": str(uuid4()), "filename": filename, "size": size, "status": "ready",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


_documents: list[dict[str, str | int]] = [_document(_SAMPLE_NAME, 128)]


class DemoQuestion(BaseModel):
    message: str
    stream: bool
    session_id: str | None = None


@app.get("/documents")
async def list_documents() -> dict[str, object]:
    return {"documents": _documents[:50], "truncated": len(_documents) > 50}


@app.post("/documents/upload", status_code=201)
async def upload_document(file: UploadFile = File(...)) -> dict[str, str | int]:
    """Pretend to accept a document without retaining any file content."""
    try:
        metadata = validate_upload_metadata(file)
    except UnsafeFilenameError as exc:
        raise HTTPException(400, "The uploaded filename is invalid.") from exc
    except UnsupportedDocumentTypeError as exc:
        raise HTTPException(415, "The uploaded file type is not supported.") from exc
    size = len(await file.read(MAX_UPLOAD_SIZE + 1))
    if size > MAX_UPLOAD_SIZE:
        raise HTTPException(413)
    if size == 0:
        raise HTTPException(400)
    item = _document(metadata.filename, size)
    _documents.insert(0, item)
    return item


def _event(payload: object, name: str | None = None) -> str:
    prefix = f"event: {name}\n" if name is not None else ""
    return prefix + f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@app.post("/chat")
async def chat(request: DemoQuestion) -> StreamingResponse:
    """Emit separated deltas and deterministic tool/source combinations."""
    question = request.message.strip()
    if not request.stream or not question:
        raise HTTPException(422)
    if question == "文档列表":
        tool = "list_documents"
        deltas = ("这是模拟的目录回复。", f"\n当前有 {len(_documents)} 份演示文档。")
        sources = []
    else:
        tool = "search_knowledge_base"
        deltas = ("先在系统登记设备。", "\n再提交审批申请。", "\n审批通过后领取，并按约定归还。")
        sources = [{"filename": _SAMPLE_NAME, "page": 1}]

    async def events() -> AsyncIterator[str]:
        for delta in deltas:
            yield _event({"delta": delta})
            await asyncio.sleep(_PAUSE_SECONDS)
            if question == "演示断流":
                return
            if question == "演示错误":
                yield _event({"message": "Demo generation failure."}, "error")
                return
        yield _event({"sources": sources}, "sources")
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        events(), media_type="text/event-stream",
        headers={"X-Session-ID": request.session_id or str(uuid4()), "X-Agent-Tool": tool},
    )
