"""Opt-in real PostgreSQL acceptance for Day 10 BM25 refresh behavior."""

from __future__ import annotations

import os
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from backend.app.core.database import get_session_factory
from backend.app.models.chunk import Chunk
from backend.app.models.document import Document
from backend.app.services.bm25 import BM25Service, load_bm25_chunks

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    os.environ.get("RUN_POSTGRES_INTEGRATION") != "1",
    reason="set RUN_POSTGRES_INTEGRATION=1 for the local PostgreSQL test",
)
def test_real_postgres_bm25_search_filter_and_refresh() -> None:
    """Load ready rows, observe add/update/delete, and cascade-clean fixtures."""
    factory = get_session_factory()
    first_doc_id = uuid4()
    second_doc_id = uuid4()
    first_chunk_id = uuid4()
    second_chunk_id = uuid4()
    first_document = Document(
        id=first_doc_id,
        filename="day10-first.txt",
        size=100,
        status="ready",
        extracted_text="Day 10 BM25 first fixture",
    )
    second_document = Document(
        id=second_doc_id,
        filename="day10-second.txt",
        size=100,
        status="ready",
        extracted_text="Day 10 BM25 second fixture",
    )
    try:
        with factory() as session:
            session.add_all([first_document, second_document])
            session.flush()
            session.add_all(
                [
                    Chunk(
                        chunk_id=first_chunk_id,
                        doc_id=first_doc_id,
                        chunk_index=0,
                        content=(
                            "中文制度编号 ZXDAY10-913847，远程支持分机为 913847。"
                            "共享编号 ZXDAY10-SHARED-300001。"
                        ),
                        page=1,
                        chunk_metadata={"fixture": "day10"},
                    ),
                    Chunk(
                        chunk_id=second_chunk_id,
                        doc_id=second_doc_id,
                        chunk_index=0,
                        content=(
                            "采购编号 ZXDAY10-551209 由采购组处理。"
                            "共享编号 ZXDAY10-SHARED-300001。"
                        ),
                        page=1,
                        chunk_metadata={"fixture": "day10"},
                    ),
                ]
            )
            session.commit()

        service = BM25Service(
            lambda: load_bm25_chunks(session_factory=factory)
        )
        first_results = service.search("ＺＸＤＡＹ１０-９１３８４７")
        assert first_results[0].chunk_id == first_chunk_id
        assert first_results[0].filename == "day10-first.txt"

        filtered = service.search(
            "ZXDAY10-SHARED-300001",
            top_k=1,
            doc_id=second_doc_id,
        )
        assert [result.chunk_id for result in filtered] == [second_chunk_id]

        added_chunk_id = uuid4()
        with factory() as session:
            session.add(
                Chunk(
                    chunk_id=added_chunk_id,
                    doc_id=first_doc_id,
                    chunk_index=1,
                    content="新增编号 ZXDAY10-NEW-772211 已进入索引。",
                    page=2,
                    chunk_metadata={"fixture": "day10"},
                )
            )
            session.commit()

        added = service.search("772211")
        assert added[0].chunk_id == added_chunk_id

        with factory() as session:
            chunk = session.get(Chunk, added_chunk_id)
            assert chunk is not None
            chunk.content = "修改编号 ZXDAY10-UPD-882244 已刷新。"
            session.commit()

        assert service.search("772211") == []
        updated = service.search("882244")
        assert updated[0].chunk_id == added_chunk_id

        with factory() as session:
            chunk = session.get(Chunk, added_chunk_id)
            assert chunk is not None
            session.delete(chunk)
            session.commit()

        assert service.search("882244") == []

        with factory() as session:
            document = session.get(Document, first_doc_id)
            assert document is not None
            session.delete(document)
            session.commit()
            assert session.scalars(
                select(Chunk).where(Chunk.doc_id == first_doc_id)
            ).all() == []
    finally:
        _delete_documents((first_doc_id, second_doc_id))


def _delete_documents(document_ids: tuple[UUID, ...]) -> None:
    """Best-effort fixture cleanup using database cascade semantics."""
    factory = get_session_factory()
    with factory() as session:
        for document_id in document_ids:
            document = session.get(Document, document_id)
            if document is not None:
                session.delete(document)
        session.commit()
