"""Protected recent chat traces for Day 19 observability."""

from datetime import datetime
from hmac import compare_digest
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from loguru import logger
from pydantic import BaseModel, ConfigDict

from backend.app.core.config import get_admin_trace_settings
from backend.app.services.request_trace import RequestTraceStore, get_request_trace_store

router = APIRouter()
_NO_STORE = {"Cache-Control": "no-store"}


class TraceResponse(BaseModel):
    """Only the bounded fields deliberately retained by the recorder."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    finished_at: datetime
    session_id: UUID | None
    mode: str
    model: str | None
    query: str | None
    standalone_query: str | None
    answer: str | None
    tool_calls: list[dict[str, object]]
    retrieved_docs: list[dict[str, object]]
    sources: list[dict[str, object]]
    model_calls: list[dict[str, object]]
    prompt_tokens: int | None
    completion_tokens: int | None
    usage_complete: bool
    latency_ms: float
    outcome: str
    http_status: int
    error_code: str | None
    business_committed: bool


def require_admin_token(
    x_admin_token: Annotated[str | None, Header(alias="X-Admin-Token")] = None,
) -> None:
    """Deny reads unless a process-provided secret matches in constant time."""
    configured = get_admin_trace_settings().token
    secret = configured.get_secret_value().strip() if configured is not None else ""
    if not secret:
        raise HTTPException(503, "Trace access is unavailable.", headers=_NO_STORE)
    supplied = x_admin_token or ""
    if not compare_digest(secret.encode("utf-8"), supplied.encode("utf-8")):
        raise HTTPException(403, "Trace access denied.", headers=_NO_STORE)


@router.get("/admin/traces", response_model=list[TraceResponse], dependencies=[Depends(require_admin_token)])
def recent_traces(
    response: Response,
    store: Annotated[RequestTraceStore, Depends(get_request_trace_store)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[TraceResponse]:
    """Read the newest N rows, with a deterministic tie break by trace ID."""
    response.headers["Cache-Control"] = "no-store"
    try:
        return [TraceResponse.model_validate(row) for row in store.recent(limit)]
    except Exception as exc:
        logger.error("Chat trace query failed: {}", type(exc).__name__)
        raise HTTPException(503, "Trace access is unavailable.", headers=_NO_STORE) from exc
