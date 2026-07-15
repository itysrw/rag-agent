"""Safe, bounded storage for untrusted uploaded documents."""

import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from uuid import UUID

from fastapi import UploadFile

from backend.app.core.config import DocumentSettings

ALLOWED_CONTENT_TYPES: dict[str, frozenset[str]] = {
    ".pdf": frozenset({"application/pdf"}),
    ".md": frozenset({"text/markdown", "text/x-markdown", "text/plain"}),
    ".txt": frozenset({"text/plain"}),
}


@dataclass(frozen=True, slots=True)
class UploadMetadata:
    """Validated client metadata used only for routing and display."""

    filename: str
    extension: str


@dataclass(frozen=True, slots=True)
class UploadPaths:
    """Temporary and final paths for one generated document identifier."""

    part: Path
    final: Path


class DocumentStorageError(RuntimeError):
    """Base class for upload storage failures."""


class UnsafeFilenameError(DocumentStorageError):
    """Raised when a client filename contains a path or unsafe characters."""


class UnsupportedDocumentTypeError(DocumentStorageError):
    """Raised when extension, MIME type, or content signature is unsupported."""


class EmptyDocumentError(DocumentStorageError):
    """Raised when the uploaded stream contains no bytes."""


class DocumentTooLargeError(DocumentStorageError):
    """Raised when actual bytes exceed the configured limit."""


def validate_upload_metadata(upload: UploadFile) -> UploadMetadata:
    """Validate an untrusted filename, extension, and declared MIME type."""
    filename = (upload.filename or "").strip()
    if not filename or len(filename) > 255:
        raise UnsafeFilenameError("The uploaded filename is invalid")
    if filename in {".", ".."} or any(ord(character) < 32 for character in filename):
        raise UnsafeFilenameError("The uploaded filename is invalid")
    if PurePosixPath(filename).name != filename:
        raise UnsafeFilenameError("The uploaded filename contains a path")
    if PureWindowsPath(filename).name != filename:
        raise UnsafeFilenameError("The uploaded filename contains a path")

    extension = Path(filename).suffix.lower()
    allowed_content_types = ALLOWED_CONTENT_TYPES.get(extension)
    if allowed_content_types is None:
        raise UnsupportedDocumentTypeError("The file extension is not supported")

    content_type = (upload.content_type or "").split(";", maxsplit=1)[0].strip().lower()
    if content_type not in allowed_content_types:
        raise UnsupportedDocumentTypeError("The declared file type is not supported")
    return UploadMetadata(filename=filename, extension=extension)


def build_upload_paths(
    upload_dir: Path,
    document_id: UUID,
    extension: str,
) -> UploadPaths:
    """Derive all storage paths in one place from a UUID and normalized suffix."""
    normalized_extension = extension.lower()
    if normalized_extension not in ALLOWED_CONTENT_TYPES:
        raise UnsupportedDocumentTypeError("The file extension is not supported")
    return UploadPaths(
        part=upload_dir / f"{document_id}.part",
        final=upload_dir / f"{document_id}{normalized_extension}",
    )


def save_upload_to_part(
    upload: UploadFile,
    paths: UploadPaths,
    settings: DocumentSettings,
    extension: str,
) -> int:
    """Stream an upload to its temporary path and return actual bytes written."""
    try:
        paths.part.parent.mkdir(parents=True, exist_ok=True)
        size = 0
        with paths.part.open("xb") as destination:
            while chunk := upload.file.read(settings.read_chunk_size):
                size += len(chunk)
                if size > settings.max_upload_size:
                    raise DocumentTooLargeError("The upload exceeds the size limit")
                destination.write(chunk)

        if size == 0:
            raise EmptyDocumentError("The uploaded file is empty")
        _validate_stored_content(paths.part, extension)
        return size
    except DocumentStorageError:
        _unlink_if_present(paths.part)
        raise
    except OSError as exc:
        _unlink_if_present(paths.part)
        raise DocumentStorageError("The upload could not be written") from exc


def promote_upload(paths: UploadPaths) -> None:
    """Atomically replace the final path with the fully validated part file."""
    try:
        os.replace(paths.part, paths.final)
    except OSError as exc:
        raise DocumentStorageError("The upload could not be finalized") from exc


def cleanup_upload_files(paths: UploadPaths) -> bool:
    """Best-effort removal of both temporary and promoted upload files."""
    part_removed = _unlink_if_present(paths.part)
    final_removed = _unlink_if_present(paths.final)
    return part_removed and final_removed


def _validate_stored_content(path: Path, extension: str) -> None:
    if extension == ".pdf":
        try:
            with path.open("rb") as source:
                header = source.read(1024)
        except OSError as exc:
            raise DocumentStorageError("The upload could not be inspected") from exc
        if b"%PDF-" not in header:
            raise UnsupportedDocumentTypeError("The uploaded content is not a PDF")


def _unlink_if_present(path: Path) -> bool:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        return False
    return True
