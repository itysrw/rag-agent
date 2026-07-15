"""Multipart document upload, parsing, persistence, and safe error mapping."""

from collections.abc import Iterator
from datetime import datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from loguru import logger
from pydantic import BaseModel, ValidationError
from sqlalchemy.exc import OperationalError, SQLAlchemyError, TimeoutError
from sqlalchemy.orm import Session
from sqlalchemy.orm.session import SessionTransactionState

from backend.app.core.config import DocumentSettings, get_document_settings
from backend.app.core.database import (
    DatabaseConfigurationError,
    get_session_factory,
)
from backend.app.models.document import Document
from backend.app.services.document_parser import (
    EncryptedPdfError,
    InvalidPdfError,
    InvalidTextEncodingError,
    NoExtractableTextError,
    PdfPageLimitError,
    parse_document,
    serialize_pages,
)
from backend.app.services.document_storage import (
    DocumentStorageError,
    DocumentTooLargeError,
    EmptyDocumentError,
    UnsafeFilenameError,
    UnsupportedDocumentTypeError,
    UploadPaths,
    build_upload_paths,
    cleanup_upload_files,
    promote_upload,
    save_upload_to_part,
    validate_upload_metadata,
)

router = APIRouter()


class DocumentUploadResponse(BaseModel):
    """Metadata returned after a complete document upload transaction."""

    id: UUID
    filename: str
    size: int
    status: str
    created_at: datetime


def require_database_session() -> Iterator[Session]:
    """Resolve a session without making database health an app startup concern."""
    try:
        session_factory = get_session_factory()
    except (DatabaseConfigurationError, ValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The document database is unavailable.",
        ) from exc

    with session_factory() as session:
        yield session


@router.post(
    "/documents/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    file: Annotated[UploadFile, File(...)],
    session: Annotated[Session, Depends(require_database_session)],
    settings: Annotated[DocumentSettings, Depends(get_document_settings)],
) -> DocumentUploadResponse:
    """Store, parse, and persist one supported document as one operation."""
    document_id = uuid4()
    paths: UploadPaths | None = None

    try:
        metadata = validate_upload_metadata(file)
        paths = build_upload_paths(
            settings.upload_dir,
            document_id,
            metadata.extension,
        )
        size = save_upload_to_part(file, paths, settings, metadata.extension)
        pages = parse_document(
            paths.part,
            metadata.extension,
            max_pdf_pages=settings.max_pdf_pages,
            read_chunk_size=settings.read_chunk_size,
        )

        document = Document(
            id=document_id,
            filename=metadata.filename,
            size=size,
            status="ready",
            extracted_text=serialize_pages(pages),
        )
        with session.begin():
            session.add(document)
            session.flush()
            promote_upload(paths)
            response = DocumentUploadResponse(
                id=document.id,
                filename=document.filename,
                size=document.size,
                status=document.status,
                created_at=document.created_at,
            )

        return response
    except UnsafeFilenameError as exc:
        _cleanup_failed_upload(session, paths, document_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded filename is invalid.",
        ) from exc
    except EmptyDocumentError as exc:
        _cleanup_failed_upload(session, paths, document_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty.",
        ) from exc
    except DocumentTooLargeError as exc:
        _cleanup_failed_upload(session, paths, document_id)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                "The uploaded file exceeds the "
                f"{_format_byte_limit(settings.max_upload_size)} limit."
            ),
        ) from exc
    except UnsupportedDocumentTypeError as exc:
        _cleanup_failed_upload(session, paths, document_id)
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="The uploaded file type is not supported.",
        ) from exc
    except EncryptedPdfError as exc:
        _cleanup_failed_upload(session, paths, document_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Encrypted PDF files are not supported.",
        ) from exc
    except PdfPageLimitError as exc:
        _cleanup_failed_upload(session, paths, document_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The PDF exceeds the {settings.max_pdf_pages}-page limit.",
        ) from exc
    except InvalidTextEncodingError as exc:
        _cleanup_failed_upload(session, paths, document_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text documents must use UTF-8 encoding.",
        ) from exc
    except NoExtractableTextError as exc:
        _cleanup_failed_upload(session, paths, document_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded document contains no extractable text.",
        ) from exc
    except InvalidPdfError as exc:
        _cleanup_failed_upload(session, paths, document_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded PDF is invalid or damaged.",
        ) from exc
    except (OperationalError, TimeoutError) as exc:
        _cleanup_failed_upload(session, paths, document_id)
        logger.error("Document database unavailable: {}", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The document database is unavailable.",
        ) from exc
    except SQLAlchemyError as exc:
        _cleanup_failed_upload(session, paths, document_id)
        logger.error("Document database operation failed: {}", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The document could not be stored.",
        ) from exc
    except DocumentStorageError as exc:
        _cleanup_failed_upload(session, paths, document_id)
        logger.error("Document storage failed: {}", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The document could not be stored.",
        ) from exc
    except Exception as exc:
        _cleanup_failed_upload(session, paths, document_id)
        logger.error("Unexpected document upload failure: {}", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The document could not be stored.",
        ) from exc


def _cleanup_failed_upload(
    session: Session,
    paths: UploadPaths | None,
    document_id: UUID,
) -> None:
    transaction = session.get_transaction()
    transaction_committed = (
        transaction is not None
        and transaction._state is SessionTransactionState.COMMITTED
    )

    if not transaction_committed:
        try:
            session.rollback()
        except SQLAlchemyError as exc:
            logger.warning("Document rollback failed: {}", type(exc).__name__)

    if (
        not transaction_committed
        and paths is not None
        and not cleanup_upload_files(paths)
    ):
        logger.warning("Document file cleanup was incomplete for {}", document_id)


def _format_byte_limit(limit: int) -> str:
    mebibyte = 1024 * 1024
    if limit % mebibyte == 0:
        return f"{limit // mebibyte} MiB"
    return f"{limit} bytes"
