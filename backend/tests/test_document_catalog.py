"""Read-only catalog SQL, bounds, lazy dependencies and safe errors."""

from collections.abc import Iterator
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import OperationalError, ProgrammingError, TimeoutError as SQLTimeoutError
from sqlalchemy.orm import Session

from backend.app.core.database import Base, DatabaseConfigurationError
from backend.app.models.chunk import Chunk
from backend.app.models.document import Document
from backend.app.services import document_catalog as module
from backend.app.services.document_catalog import (
    DocumentCatalogError, DocumentCatalogService, DocumentCatalogUnavailableError,
)


def catalog_with_rows(count: int) -> tuple[DocumentCatalogService, list[tuple[str, Any]], Any]:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        for index in range(count):
            session.add(Document(
                id=UUID(int=index + 1), filename=f"制度中文-{index}.pdf", size=index + 100,
                status="ready", created_at=datetime(2026, 10, 30, tzinfo=timezone.utc) +
                timedelta(days=index % 2), extracted_text="private source body",
            ))
        session.add(Document(id=UUID(int=999), filename="pending.txt", size=1,
                             status="pending", extracted_text="private pending body"))
        session.flush()
        if count:
            session.add_all([Chunk(doc_id=UUID(int=1), chunk_index=index, page=1,
                                   content="private chunk body", chunk_metadata={}) for index in range(2)])
        session.commit()
    queries: list[tuple[str, Any]] = []
    event.listen(engine, "before_cursor_execute",
                 lambda conn, cursor, statement, params, context, many: queries.append((statement, params)))
    return DocumentCatalogService(lambda: Session(engine)), queries, engine


@pytest.mark.parametrize("count", [0, 1, 50, 51])
def test_ready_list_is_bounded_and_stably_sorted(count: int) -> None:
    service, queries, engine = catalog_with_rows(count)
    try:
        result = service.list_documents()
        assert len(result.documents) == min(count, 50)
        assert result.truncated is (count > 50)
        expected = sorted(range(count), key=lambda index: (-(index % 2), index + 1))[:50]
        assert [item.id for item in result.documents] == [UUID(int=index + 1) for index in expected]
        assert all(item.status == "ready" for item in result.documents)
        assert len(queries) == 1
        sql, params = queries[0]
        assert "extracted_text" not in sql and "chunks.content" not in sql
        assert "ORDER BY documents.created_at DESC, documents.id ASC" in sql
        assert "LIMIT" in sql and 51 in params
        if result.documents:
            assert result.documents[0].filename.startswith("制度中文")
            assert not hasattr(result.documents[0], "extracted_text")
            with pytest.raises(FrozenInstanceError):
                result.documents[0].size = 0
    finally:
        engine.dispose()


def test_detail_counts_chunks_without_loading_any_source_text() -> None:
    service, queries, engine = catalog_with_rows(2)
    try:
        detail = service.get_document_detail(UUID(int=1))
        assert detail is not None
        assert detail.id == UUID(int=1) and detail.chunk_count == 2
        assert detail.filename == "制度中文-0.pdf" and detail.size == 100
        assert not hasattr(detail, "extracted_text") and not hasattr(detail, "content")
        empty = service.get_document_detail(UUID(int=2))
        assert empty is not None and empty.chunk_count == 0
        assert service.get_document_detail(UUID(int=999)) is None
        assert service.get_document_detail(UUID(int=888)) is None
        assert len(queries) == 4
        assert all("extracted_text" not in sql and "chunks.content" not in sql for sql, _ in queries)
        assert "count(chunks.chunk_id)" in queries[0][0]
    finally:
        engine.dispose()


def test_catalog_factory_defers_database_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[bool] = []
    def unavailable() -> None:
        calls.append(True)
        raise DatabaseConfigurationError("private configuration")
    monkeypatch.setattr(module, "get_session_factory", unavailable)
    module.get_document_catalog_service.cache_clear()
    try:
        service = module.get_document_catalog_service()
        assert calls == []
        with pytest.raises(DocumentCatalogUnavailableError) as error:
            service.list_documents()
        assert calls == [True] and "private" not in str(error.value)
    finally:
        module.get_document_catalog_service.cache_clear()


@pytest.mark.parametrize(("failure", "expected"), [
    (DatabaseConfigurationError("private"), DocumentCatalogUnavailableError),
    (OperationalError("private sql", {}, RuntimeError("private")), DocumentCatalogUnavailableError),
    (SQLTimeoutError("private timeout"), DocumentCatalogUnavailableError),
    (TimeoutError("private timeout"), DocumentCatalogUnavailableError),
    (ProgrammingError("private sql", {}, RuntimeError("private")), DocumentCatalogError),
])
@pytest.mark.parametrize("detail", [False, True])
def test_catalog_maps_configuration_connection_and_internal_sql_failures(
    failure: Exception, expected: type[DocumentCatalogError], detail: bool,
) -> None:
    closed: list[bool] = []
    class BrokenSession:
        def __enter__(self) -> "BrokenSession":
            return self
        def __exit__(self, *args: Any) -> None:
            closed.append(True)
        def execute(self, statement: Any) -> Any:
            raise failure
    service = DocumentCatalogService(BrokenSession)
    with pytest.raises(expected) as error:
        service.get_document_detail(UUID(int=1)) if detail else service.list_documents()
    assert type(error.value) is expected
    assert "private" not in str(error.value) and closed == [True]
