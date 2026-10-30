"""Bounded, lazy, read-only access to ready-document metadata."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import (
    DBAPIError, DisconnectionError, InterfaceError, OperationalError,
    SQLAlchemyError, TimeoutError as SQLTimeoutError,
)
from sqlalchemy.orm import Session

from backend.app.core.database import DatabaseConfigurationError, get_session_factory
from backend.app.models.chunk import Chunk
from backend.app.models.document import Document

DOCUMENT_LIST_LIMIT = 50


class DocumentCatalogError(RuntimeError):
    """A safe internal catalog query failure."""


class DocumentCatalogUnavailableError(DocumentCatalogError):
    """Configuration, connection, or timeout prevents catalog access."""


@dataclass(frozen=True, slots=True)
class DocumentListItem:
    """Only the public metadata columns, with no source text or storage path."""

    id: UUID
    filename: str
    size: int
    status: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class DocumentDetail(DocumentListItem):
    """Metadata plus an aggregate count; Chunk content is never selected."""

    chunk_count: int


@dataclass(frozen=True, slots=True)
class DocumentListResult:
    documents: tuple[DocumentListItem, ...]
    truncated: bool


_COLUMNS = (Document.id, Document.filename, Document.size, Document.status, Document.created_at)


class DocumentCatalogService:
    """Create a Session only when a list/detail tool actually runs."""

    def __init__(self, session_factory: Callable[[], Session] | None = None) -> None:
        self._session_factory = session_factory

    @contextmanager
    def _session(self) -> Iterator[Session]:
        try:
            factory = self._session_factory or get_session_factory()
            with factory() as session:
                yield session
        except (DatabaseConfigurationError, ValidationError, OperationalError,
                InterfaceError, DisconnectionError, SQLTimeoutError, TimeoutError) as exc:
            raise DocumentCatalogUnavailableError("The document catalog is unavailable.") from exc
        except DBAPIError as exc:
            if exc.connection_invalidated:
                raise DocumentCatalogUnavailableError("The document catalog is unavailable.") from exc
            raise DocumentCatalogError("The document catalog query failed.") from exc
        except SQLAlchemyError as exc:
            raise DocumentCatalogError("The document catalog query failed.") from exc

    def list_documents(self) -> DocumentListResult:
        """Read at most 51 rows to return 50 items and a truthful truncated flag."""
        statement = (select(*_COLUMNS).where(Document.status == "ready")
                     .order_by(Document.created_at.desc(), Document.id.asc())
                     .limit(DOCUMENT_LIST_LIMIT + 1))
        with self._session() as session:
            rows = session.execute(statement).all()
            documents = tuple(DocumentListItem(*row) for row in rows[:DOCUMENT_LIST_LIMIT])
        return DocumentListResult(documents, len(rows) > DOCUMENT_LIST_LIMIT)

    def get_document_detail(self, doc_id: UUID) -> DocumentDetail | None:
        """Count all matching Chunks in SQL without selecting either text column."""
        if not isinstance(doc_id, UUID):
            raise ValueError("doc_id must be a UUID")
        statement = (select(*_COLUMNS, func.count(Chunk.chunk_id))
                     .outerjoin(Chunk, Chunk.doc_id == Document.id)
                     .where(Document.id == doc_id, Document.status == "ready")
                     .group_by(*_COLUMNS))
        with self._session() as session:
            row = session.execute(statement).first()
            return None if row is None else DocumentDetail(*row)


@lru_cache
def get_document_catalog_service() -> DocumentCatalogService:
    """Construct a process-local adapter without resolving database settings."""
    return DocumentCatalogService()
