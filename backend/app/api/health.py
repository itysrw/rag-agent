"""Process liveness endpoint."""

from fastapi import APIRouter, status

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health() -> dict[str, str]:
    """Report whether the API process is alive."""
    return {"status": "ok"}
