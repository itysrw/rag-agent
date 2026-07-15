"""Chat endpoint placeholder for Day 3."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, StringConstraints

router = APIRouter()


class ChatRequest(BaseModel):
    """Minimal chat request accepted during Day 2."""

    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


@router.post("/chat", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def chat(request: ChatRequest) -> None:
    """Reserve the chat route until the LLM client is implemented."""
    del request
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Chat is not implemented yet; it will be available in Day 3.",
    )
