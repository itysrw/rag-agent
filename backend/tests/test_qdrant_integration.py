"""Opt-in real Qdrant collection, upsert, retrieve, and query acceptance."""

import os
from pathlib import Path
from uuid import uuid4

import pytest
from qdrant_client import QdrantClient
from qdrant_client.http import models

from backend.app.core.config import EmbeddingSettings, PROJECT_ROOT, QdrantSettings
from backend.app.services.document_parser import parse_document
from backend.app.services.embedding import EmbeddingClient
from backend.app.services.qdrant_store import QdrantVectorStore, VectorizedChunk
from backend.app.services.text_splitter import split_pages
from backend.tests.pdf_fixtures import build_text_pdf

pytestmark = pytest.mark.integration


def basis_vector(position: int) -> tuple[float, ...]:
    """Return one normalized vector for deterministic nearest-neighbor checks."""
    values = [0.0] * 512
    values[position] = 1.0
    return tuple(values)


@pytest.mark.skipif(
    os.environ.get("RUN_QDRANT_INTEGRATION") != "1",
    reason="set RUN_QDRANT_INTEGRATION=1 for the local Qdrant test",
)
def test_real_qdrant_is_idempotent_and_returns_payload_without_vectors() -> None:
    """Use a unique collection and always remove it after real REST operations."""
    collection = f"day7_test_{uuid4().hex}"
    settings = QdrantSettings(
        _env_file=None,
        host="127.0.0.1",
        port=6333,
        collection=collection,
    )
    client = QdrantClient(
        url=settings.build_url(),
        timeout=settings.timeout_seconds,
        prefer_grpc=False,
    )
    store = QdrantVectorStore(settings, client=client)
    doc_id = uuid4()
    chunks = [
        VectorizedChunk(
            chunk_id=uuid4(),
            doc_id=doc_id,
            chunk_index=index,
            content=f"integration-content-{index}",
            page=index + 1,
            filename="integration.pdf",
            metadata={"token_count": index + 1},
            vector=basis_vector(index),
        )
        for index in range(2)
    ]

    try:
        store.initialize_collection()
        collection_info = client.get_collection(collection)
        vectors = collection_info.config.params.vectors
        assert isinstance(vectors, models.VectorParams)
        assert vectors.size == 512
        assert vectors.distance == models.Distance.COSINE

        assert store.upsert_chunks(chunks) == 2
        assert store.upsert_chunks(chunks) == 2

        retrieved = client.retrieve(
            collection_name=collection,
            ids=[str(chunk.chunk_id) for chunk in chunks],
            with_payload=True,
            with_vectors=False,
        )
        assert len(retrieved) == 2
        assert {str(point.id) for point in retrieved} == {
            str(chunk.chunk_id) for chunk in chunks
        }
        assert all(point.vector is None for point in retrieved)

        results = store.search(basis_vector(0), limit=5)
        assert len(results) == 2
        assert results[0].chunk_id == chunks[0].chunk_id
        assert results[0].content == "integration-content-0"
        assert results[0].page == 1
    finally:
        if client.collection_exists(collection):
            client.delete_collection(collection_name=collection)
        client.close()


@pytest.mark.skipif(
    os.environ.get("RUN_QDRANT_INTEGRATION") != "1",
    reason="set RUN_QDRANT_INTEGRATION=1 for the local Qdrant test",
)
def test_real_qdrant_doc_id_filter_returns_only_the_requested_document() -> None:
    """Two interleaved documents stay separated by the in-query filter."""
    collection = f"day9_filter_{uuid4().hex}"
    settings = QdrantSettings(
        _env_file=None,
        host="127.0.0.1",
        port=6333,
        collection=collection,
    )
    client = QdrantClient(
        url=settings.build_url(),
        timeout=settings.timeout_seconds,
        prefer_grpc=False,
    )
    store = QdrantVectorStore(settings, client=client)
    first_doc = uuid4()
    second_doc = uuid4()
    chunks = [
        VectorizedChunk(
            chunk_id=uuid4(),
            doc_id=doc_id,
            chunk_index=index,
            content=f"filter-content-{index}",
            page=index + 1,
            filename=f"{label}.pdf",
            metadata={"token_count": index + 1},
            vector=basis_vector(index),
        )
        for index, (doc_id, label) in enumerate(
            [
                (first_doc, "first"),
                (second_doc, "second"),
                (first_doc, "first"),
                (second_doc, "second"),
            ]
        )
    ]

    try:
        store.initialize_collection()
        assert store.upsert_chunks(chunks) == 4

        unfiltered = store.search(basis_vector(0), limit=5)
        assert {result.doc_id for result in unfiltered} == {first_doc, second_doc}

        for target_doc in (first_doc, second_doc):
            filtered = store.search(basis_vector(0), limit=5, doc_id=target_doc)
            expected_ids = {
                chunk.chunk_id for chunk in chunks if chunk.doc_id == target_doc
            }
            assert len(filtered) == 2
            assert {result.chunk_id for result in filtered} == expected_ids
            assert all(result.doc_id == target_doc for result in filtered)

        assert store.search(basis_vector(0), limit=5, doc_id=uuid4()) == []
    finally:
        if client.collection_exists(collection):
            client.delete_collection(collection_name=collection)
        client.close()


@pytest.mark.skipif(
    os.environ.get("RUN_QDRANT_INTEGRATION") != "1"
    or os.environ.get("RUN_LOCAL_EMBEDDING_INTEGRATION") != "1",
    reason="enable both real Qdrant and local BGE integration tests",
)
def test_controlled_pdf_queries_return_the_correct_page_at_top_one(
    tmp_path: Path,
) -> None:
    """Run the controlled three-page relevance smoke through real BGE and Qdrant."""
    collection = f"day7_relevance_{uuid4().hex}"
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
    store = QdrantVectorStore(qdrant_settings, client=qdrant_client)
    embedding_client = EmbeddingClient(
        EmbeddingSettings(
            _env_file=None,
            cache_dir=PROJECT_ROOT / "data" / "models",
        )
    )
    pdf_path = tmp_path / "day7-controlled.pdf"
    pdf_path.write_bytes(
        build_text_pdf(
            [
                "报销票据必须在每月二十五日前提交给财务组。",
                "VPN 故障请联系网络组，服务分机是 6203。",
                "年假申请需要至少提前三个工作日提交。",
            ]
        )
    )
    pages = parse_document(
        pdf_path,
        ".pdf",
        max_pdf_pages=10,
        read_chunk_size=1024 * 1024,
    )
    drafts = split_pages(
        pages,
        chunk_size=500,
        chunk_overlap=100,
        encoding_name="o200k_base",
    )
    vectors = embedding_client.embed_documents([draft.content for draft in drafts])
    doc_id = uuid4()
    vectorized = [
        VectorizedChunk(
            chunk_id=uuid4(),
            doc_id=doc_id,
            chunk_index=draft.chunk_index,
            content=draft.content,
            page=draft.page,
            filename=pdf_path.name,
            metadata=dict(draft.metadata),
            vector=vector,
        )
        for draft, vector in zip(drafts, vectors, strict=True)
    ]
    questions = [
        ("报销票据最晚什么时候交？", 1),
        ("VPN 连不上应该联系谁，分机是多少？", 2),
        ("年假需要提前多久申请？", 3),
    ]

    try:
        store.initialize_collection()
        assert store.upsert_chunks(vectorized) == 3
        for query, expected_page in questions:
            results = store.search(embedding_client.embed_query(query), limit=5)
            assert expected_page in [result.page for result in results[:3]]
            assert results[0].page == expected_page, [
                (result.page, result.score) for result in results
            ]
    finally:
        if qdrant_client.collection_exists(collection):
            qdrant_client.delete_collection(collection_name=collection)
        qdrant_client.close()
