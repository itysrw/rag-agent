"""Upload media types shared by the backend and Streamlit client."""

UPLOAD_CONTENT_TYPES: dict[str, tuple[str, ...]] = {
    ".pdf": ("application/pdf",),
    ".md": ("text/markdown", "text/x-markdown", "text/plain"),
    ".txt": ("text/plain",),
}
