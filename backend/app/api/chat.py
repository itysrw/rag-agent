"""OpenAI-compatible chat endpoint with complete and SSE responses."""

import json
from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel, StringConstraints
from starlette.responses import StreamingResponse

from backend.app.services.llm import (
    LLMClient,
    LLMConfigurationError,
    LLMServiceError,
    get_llm_client,
)

router = APIRouter()


class ChatRequest(BaseModel):
    """One user message and the desired response mode."""

    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    stream: bool = False


class ChatResponse(BaseModel):
    """Complete language model response."""

    answer: str
    model: str


def require_llm_client() -> LLMClient:
    """Resolve the configured client or return a safe service error."""
    try:
        return get_llm_client()
    except LLMConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The language model is not configured.",
        ) from exc


def stream_sse(client: LLMClient, message: str) -> Iterator[str]:
    """Encode language model deltas as Server-Sent Events."""
    try:
        for delta in client.stream(message):
            payload = json.dumps({"delta": delta}, ensure_ascii=False)
            yield f"data: {payload}\n\n"
        yield "data: [DONE]\n\n"
    except LLMServiceError:
        logger.exception("Language model stream failed")
        payload = json.dumps(
            {"detail": "The language model stream failed."},
            ensure_ascii=False,
        )
        yield f"event: error\ndata: {payload}\n\n"


@router.post("/chat", response_model=None)
def chat(
    request: ChatRequest,
    client: Annotated[LLMClient, Depends(require_llm_client)],
) -> ChatResponse | StreamingResponse:
    """Return either a complete JSON answer or an SSE stream."""
    if request.stream:
        return StreamingResponse(
            stream_sse(client, request.message),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    try:
        answer = client.complete(request.message)
    except LLMServiceError as exc:
        logger.exception("Language model request failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The language model request failed.",
        ) from exc

    return ChatResponse(answer=answer, model=client.model)
