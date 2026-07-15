"""Tests for bounded and traversal-safe upload storage."""

from io import BytesIO
from pathlib import Path
from uuid import UUID

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from backend.app.core.config import DocumentSettings
from backend.app.services.document_storage import (
    DocumentTooLargeError,
    UnsafeFilenameError,
    UnsupportedDocumentTypeError,
    build_upload_paths,
    save_upload_to_part,
    validate_upload_metadata,
)


class RecordingBytesIO(BytesIO):
    """Bytes stream that records requested read sizes."""

    def __init__(self, value: bytes) -> None:
        super().__init__(value)
        self.read_sizes: list[int] = []

    def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
        return super().read(size)


def make_upload(
    filename: str,
    data: bytes,
    content_type: str,
    stream_type: type[BytesIO] = BytesIO,
) -> UploadFile:
    """Build a Starlette upload with explicit untrusted metadata."""
    return UploadFile(
        file=stream_type(data),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


def make_settings(tmp_path: Path, **overrides: int) -> DocumentSettings:
    """Build isolated storage limits without loading the repository .env."""
    return DocumentSettings(
        _env_file=None,
        upload_dir=tmp_path,
        max_upload_size=overrides.get("max_upload_size", 1024),
        max_pdf_pages=10,
        read_chunk_size=overrides.get("read_chunk_size", 4),
    )


@pytest.mark.parametrize(
    "filename",
    ["../secret.txt", "..\\secret.txt", "folder/file.txt", "C:\\temp\\file.txt"],
)
def test_filename_paths_are_rejected(filename: str) -> None:
    """Both POSIX and Windows traversal syntax is invalid."""
    upload = make_upload(filename, b"hello", "text/plain")

    with pytest.raises(UnsafeFilenameError):
        validate_upload_metadata(upload)


def test_extension_and_mime_must_both_be_supported() -> None:
    """A trusted-looking suffix cannot override a mismatched MIME type."""
    upload = make_upload("report.pdf", b"%PDF-1.4", "text/plain")

    with pytest.raises(UnsupportedDocumentTypeError):
        validate_upload_metadata(upload)


def test_storage_name_uses_uuid_and_normalized_extension(tmp_path: Path) -> None:
    """Client names never become filesystem names."""
    document_id = UUID("12345678-1234-5678-1234-567812345678")

    paths = build_upload_paths(tmp_path, document_id, ".PDF")

    assert paths.part == tmp_path / f"{document_id}.part"
    assert paths.final == tmp_path / f"{document_id}.pdf"


def test_upload_is_read_in_configured_chunks(tmp_path: Path) -> None:
    """Storage never requests the entire upload in one read."""
    upload = make_upload("notes.txt", b"abcdefghij", "text/plain", RecordingBytesIO)
    metadata = validate_upload_metadata(upload)
    settings = make_settings(tmp_path, read_chunk_size=4)
    paths = build_upload_paths(tmp_path, UUID(int=1), metadata.extension)

    size = save_upload_to_part(upload, paths, settings, metadata.extension)

    assert size == 10
    assert paths.part.read_bytes() == b"abcdefghij"
    assert upload.file.read_sizes == [4, 4, 4, 4]


def test_actual_bytes_enforce_limit_and_part_is_removed(tmp_path: Path) -> None:
    """The actual stream size, not Content-Length, determines a 413 condition."""
    upload = make_upload("notes.txt", b"12345", "text/plain")
    metadata = validate_upload_metadata(upload)
    settings = make_settings(tmp_path, max_upload_size=4)
    paths = build_upload_paths(tmp_path, UUID(int=2), metadata.extension)

    with pytest.raises(DocumentTooLargeError):
        save_upload_to_part(upload, paths, settings, metadata.extension)

    assert not paths.part.exists()


def test_pdf_signature_mismatch_is_rejected_and_cleaned(tmp_path: Path) -> None:
    """Declared PDF metadata cannot make arbitrary content a PDF."""
    upload = make_upload("report.pdf", b"plain text", "application/pdf")
    metadata = validate_upload_metadata(upload)
    settings = make_settings(tmp_path)
    paths = build_upload_paths(tmp_path, UUID(int=3), metadata.extension)

    with pytest.raises(UnsupportedDocumentTypeError):
        save_upload_to_part(upload, paths, settings, metadata.extension)

    assert not paths.part.exists()
