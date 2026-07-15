"""Document endpoint placeholder for Day 4."""

from fastapi import APIRouter, HTTPException, status

router = APIRouter()


@router.post("/documents/upload", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def upload_document() -> None:
    """Reserve the upload route without accepting multipart data yet."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Document upload is not implemented yet; it will be available in Day 4.",
    )
