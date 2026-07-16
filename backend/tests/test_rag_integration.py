"""Opt-in upload, explicit index, and RAG HTTP integration acceptance."""

from __future__ import annotations

import os
from collections.abc import Iterator, Sequence
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from qdrant_client import QdrantClient

from backend.app.api.chat import require_rag_service
from backend.app.commands.index_document import index_document
from backend.app.core.config import (
    ChunkingSettings,
    DocumentSettings,
    EmbeddingSettings,
    PROJECT_ROOT,
    QdrantSettings,
    RAGSettings,
    get_chunking_settings,
    get_document_settings,
)
from backend.app.core.database import get_session_factory
from backend.app.main import app
from backend.app.models.document import Document
from backend.app.services.document_storage import build_upload_paths
from backend.app.services.embedding import EmbeddingClient
from backend.app.services.llm import LLMMessage
from backend.app.services.qdrant_store import QdrantVectorStore
from backend.app.services.rag import NO_RELEVANT_KNOWLEDGE, RAGService
from backend.app.services.retrieval import RetrievalService
from backend.tests.pdf_fixtures import build_text_pdf

pytestmark = pytest.mark.integration


class StubMessagesLLMClient:
    """Inspect RAG messages and return a deterministic answer without fees."""

    model = "stub-rag-model"

    def __init__(self) -> None:
        self.calls: list[tuple[LLMMessage, ...]] = []

    def complete_messages(self, messages: Sequence[LLMMessage]) -> str:
        self.calls.append(tuple(messages))
        return "报销票据应在每月二十五日前提交。[day8-e2e.pdf，第1页]"

    def stream_messages(self, messages: Sequence[LLMMessage]) -> Iterator[str]:
        self.calls.append(tuple(messages))
        yield "unused"


@pytest.mark.skipif(
    any(
        os.environ.get(flag) != "1"
        for flag in (
            "RUN_RAG_INTEGRATION",
            "RUN_POSTGRES_INTEGRATION",
            "RUN_LOCAL_EMBEDDING_INTEGRATION",
            "RUN_QDRANT_INTEGRATION",
        )
    ),
    reason="enable real PostgreSQL, local BGE, Qdrant, and RAG integration",
)
def test_upload_index_and_chat_returns_answer_source_and_safe_refusal(
    tmp_path: Path,
) -> None:
    """Exercise upload -> explicit index -> chat with real retrieval services."""
    collection = f"day8_e2e_{uuid4().hex}"
    filename = "day8-e2e.pdf"
    document_settings = DocumentSettings(
        _env_file=None,
        upload_dir=tmp_path / "uploads",
        max_upload_size=20 * 1024 * 1024,
        max_pdf_pages=500,
        read_chunk_size=1024 * 1024,
    )
    chunking_settings = ChunkingSettings(
        _env_file=None,
        chunk_size=500,
        chunk_overlap=100,
        chunk_encoding_name="o200k_base",
    )
    qdrant_settings = QdrantSettings(
        _env_file=None,
        host="127.0.0.1",
        port=6333,
        collection=collection,
    )
    qdrant_client = QdrantClient(
        url=qdrant_settings.build_url(),
        timeout=qdrant_settings.timeout_seconds,
        prefer_grpc=False,
    )
    vector_store = QdrantVectorStore(qdrant_settings, client=qdrant_client)
    embedding_client = EmbeddingClient(
        EmbeddingSettings(
            _env_file=None,
            cache_dir=PROJECT_ROOT / "data" / "models",
        )
    )
    llm_client = StubMessagesLLMClient()
    rag_service = RAGService(
        RetrievalService(embedding_client, vector_store),
        llm_client,  # type: ignore[arg-type]
        RAGSettings(_env_file=None, min_relevance_score=0.46),
    )
    pdf = build_text_pdf(
        [
            "报销票据必须在每月二十五日前提交给财务组。",
            "VPN 故障请联系网络组，服务分机是 6203。",
            "年假申请需要至少提前三个工作日提交。",
        ]
    )
    document_id: UUID | None = None
    app.dependency_overrides[get_document_settings] = lambda: document_settings
    app.dependency_overrides[get_chunking_settings] = lambda: chunking_settings
    app.dependency_overrides[require_rag_service] = lambda: rag_service
    try:
        with TestClient(app) as client:
            upload_response = client.post(
                "/documents/upload",
                files={"file": (filename, pdf, "application/pdf")},
            )
            assert upload_response.status_code == 201
            document_id = UUID(upload_response.json()["id"])

            summary = index_document(
                document_id,
                session_factory=get_session_factory(),
                embedding_client_factory=lambda: embedding_client,
                vector_store_factory=lambda: vector_store,
            )
            assert summary.chunk_count == 3

            relevant_response = client.post(
                "/chat",
                json={
                    "message": "报销票据必须在每月二十五日前提交给财务组吗？"
                },
            )
            negative_response = client.post(
                "/chat",
                json={"message": "Python 如何定义一个函数？"},
            )

        assert relevant_response.status_code == 200
        assert relevant_response.json()["sources"][0] == {
            "filename": filename,
            "page": 1,
        }
        assert all(
            source["filename"] == filename
            for source in relevant_response.json()["sources"]
        )
        assert len(llm_client.calls) == 1
        assert [message["role"] for message in llm_client.calls[0]] == [
            "system",
            "user",
        ]
        assert filename in llm_client.calls[0][1]["content"]
        assert negative_response.status_code == 200
        assert negative_response.json() == {
            "answer": NO_RELEVANT_KNOWLEDGE,
            "model": "stub-rag-model",
            "sources": [],
        }
        assert len(llm_client.calls) == 1
    finally:
        app.dependency_overrides.clear()
        try:
            if qdrant_client.collection_exists(collection):
                qdrant_client.delete_collection(collection_name=collection)
        finally:
            qdrant_client.close()
        if document_id is not None:
            try:
                with get_session_factory()() as session:
                    document = session.get(Document, document_id)
                    if document is not None:
                        session.delete(document)
                        session.commit()
            finally:
                paths = build_upload_paths(
                    document_settings.upload_dir,
                    document_id,
                    ".pdf",
                )
                paths.part.unlink(missing_ok=True)
                paths.final.unlink(missing_ok=True)
