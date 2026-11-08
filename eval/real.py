"""Explicitly authorized DeepSeek execution against a read-only frozen corpus."""

from collections import Counter, defaultdict
from collections.abc import Callable, Iterator, Sequence
from contextlib import ExitStack, contextmanager
from dataclasses import asdict, dataclass
from functools import partial
from hashlib import sha256
import json
from pathlib import Path
from uuid import UUID

import httpx
from huggingface_hub import snapshot_download
from openai import OpenAI
from pydantic import ValidationError
from qdrant_client import QdrantClient, models
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import (
    DatabaseSettings, DocumentSettings, EmbeddingSettings, LLMSettings, QdrantSettings,
    RAGSettings, RerankerSettings,
)
from backend.app.core.database import DatabaseConfigurationError, build_database_url
from backend.app.models.document import Document
from backend.app.services.bm25 import (
    BM25CorpusChunk, BM25Service, build_corpus_fingerprint, load_bm25_chunks,
)
from backend.app.services.document_catalog import DocumentCatalogService
from backend.app.services.document_storage import build_upload_paths
from backend.app.services.embedding import EmbeddingClient, ensure_model_snapshot
from backend.app.services.hybrid import HybridRetrievalService
from backend.app.services.llm import LLMClient
from backend.app.services.qdrant_store import QdrantCollectionMismatchError, QdrantVectorStore
from backend.app.services.reranker import (
    RerankOutcome, RerankedChunk, RerankedRetrievalService, RerankerService, ensure_reranker_snapshot,
)
from backend.app.services.retrieval import RetrievalService
from eval.agent import EvalAgent, EvalStop, RequestBudget
from eval.scoring import CorpusDocument

CHUNKS_PER_PDF = {
    "earthquake.pdf": 4, "flood.pdf": 5, "hurricane.pdf": 5,
    "tornado.pdf": 4, "wildfire.pdf": 3, "winter-storm.pdf": 4,
}
INGESTION_CHUNKING = {"chunk_size": 300, "chunk_overlap": 60, "encoding_name": "o200k_base"}
# Derived from parse_document + split_pages on the hash-verified Day 17 PDFs
# with INGESTION_CHUNKING, not from either store. Keep preflight tokenizer-free.
_FROZEN_CHUNK_TEXT_SHA256 = {
    "earthquake.pdf": "044f1a1168e16be7251558dd0c288716094cb203b065f86c4274a97eb2642ca1",
    "flood.pdf": "c6af3ed87c2736d33404f99c0c91bc892e588ef065207e2b0acb216c4cb9a6fa",
    "hurricane.pdf": "15b3e13f67b7851ad6f60bfde3f597b704738ecb7e952cf417b0d82f2ef52bf6",
    "tornado.pdf": "ef4bf352b0740df2e90fb29c4735a6354406d001b5f5414ee9e16ed69c192fe8",
    "wildfire.pdf": "af89c4092b9a61041324048f19e4055f664f99f2870191f1582de0c5134088e0",
    "winter-storm.pdf": "3734bd6c6675b1e1040dce4b2d8a1ec28f089134af099971253959668e8dc140",
}
SessionFactory = Callable[[], Session]


@dataclass(frozen=True, slots=True)
class CorpusSnapshot:
    documents: tuple[dict[str, str | int], ...]
    chunks: tuple[BM25CorpusChunk, ...]
    fingerprint: str


def _chunk_payload(chunk: BM25CorpusChunk | RerankedChunk) -> dict[str, object]:
    return {
        "chunk_id": str(chunk.chunk_id),
        "doc_id": str(chunk.doc_id),
        "filename": chunk.filename,
        "page": chunk.page,
        "chunk_index": chunk.chunk_index,
        "content": chunk.content,
        "metadata": chunk.metadata,
    }


def _canonical_payload(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False)


def _chunk_text_sha256(chunks: Sequence[BM25CorpusChunk]) -> str:
    entries = [(chunk.chunk_index, chunk.page, chunk.content) for chunk in chunks]
    data = json.dumps(entries, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return sha256(data).hexdigest()


def verify_points(
    chunks: Sequence[BM25CorpusChunk], points: Sequence[models.Record], *, has_more: bool,
) -> None:
    """Require exact Point identities and the same payloads as the ready PG chunks."""
    expected = {str(chunk.chunk_id): _chunk_payload(chunk) for chunk in chunks}
    point_ids = {str(point.id) for point in points}
    if has_more or len(points) != len(point_ids) or point_ids != expected.keys():
        raise EvalStop("qdrant_corpus_mismatch")
    for point in points:
        payload = point.payload
        wanted = expected[str(point.id)]
        if (not isinstance(payload, dict) or not wanted.keys() <= payload.keys()
                or _canonical_payload({key: payload[key] for key in wanted}) != _canonical_payload(wanted)):
            raise EvalStop("qdrant_payload_mismatch")


def verify_corpus(
    corpus: Sequence[CorpusDocument], upload_dir: Path, sessions: SessionFactory,
    vector_store: QdrantVectorStore, client: QdrantClient,
) -> CorpusSnapshot:
    """Read the exact six ready files and every point in the target collection."""
    expected = {item.filename: item for item in corpus}
    try:
        with sessions() as session:
            rows = session.execute(
                select(Document.id, Document.filename).where(Document.status == "ready")
                .order_by(Document.filename, Document.id).limit(len(expected) + 1)
            ).all()
            if Counter(row.filename for row in rows) != Counter(expected.keys()):
                raise EvalStop("postgres_corpus_mismatch")
            # Use the same read transaction and the same loader as BM25.
            chunks = load_bm25_chunks(session_factory=lambda: session)
        by_document = defaultdict(list)
        for chunk in chunks:
            by_document[chunk.doc_id].append(chunk)
        if set(by_document) != {row.id for row in rows}:
            raise EvalStop("postgres_chunks_mismatch")
        documents = []
        for doc_id, filename in rows:
            document = expected[filename]
            uploaded = build_upload_paths(upload_dir, doc_id, ".pdf").final
            if not uploaded.is_file() or sha256(uploaded.read_bytes()).hexdigest() != document.sha256:
                raise EvalStop("uploaded_pdf_mismatch")
            doc_chunks = by_document[doc_id]
            if (len(doc_chunks) != CHUNKS_PER_PDF[filename]
                    or [chunk.chunk_index for chunk in doc_chunks] != list(range(len(doc_chunks)))
                    or {chunk.page for chunk in doc_chunks} != set(range(1, document.page_count + 1))
                    or any(chunk.filename != filename
                           or any(chunk.metadata.get(key) != value for key, value in INGESTION_CHUNKING.items())
                           for chunk in doc_chunks)
                    or _chunk_text_sha256(doc_chunks) != _FROZEN_CHUNK_TEXT_SHA256[filename]):
                raise EvalStop("postgres_chunks_mismatch")
            documents.append({**asdict(document), "document_id": str(doc_id), "chunk_count": len(doc_chunks)})
        vector_store.validate_collection()
        points, next_offset = client.scroll(
            collection_name=vector_store.settings.collection, limit=len(chunks) + 1,
            with_payload=True, with_vectors=False,
        )
        verify_points(chunks, points, has_more=next_offset is not None)
        return CorpusSnapshot(tuple(documents), chunks, build_corpus_fingerprint(chunks))
    except EvalStop:
        raise
    except QdrantCollectionMismatchError as exc:
        raise EvalStop("qdrant_collection_mismatch") from exc
    except Exception as exc:
        raise EvalStop("corpus_preflight_unavailable") from exc


def _cached_download(**kwargs: object) -> str:
    if kwargs.get("local_files_only") is not True:
        raise EvalStop("model_cache_unavailable")
    return snapshot_download(**kwargs)


def _model_paths(
    embedding: EmbeddingSettings, reranker: RerankerSettings,
) -> tuple[Path, Path]:
    if not embedding.cache_dir.is_dir() or not reranker.cache_dir.is_dir():
        raise EvalStop("model_cache_unavailable")
    try:
        return (ensure_model_snapshot(embedding, downloader=_cached_download),
                ensure_reranker_snapshot(reranker, downloader=_cached_download))
    except Exception as exc:
        raise EvalStop("model_cache_unavailable") from exc


def _open_sdk(
    stack: ExitStack, llm: LLMSettings, api_key: str, budget: RequestBudget,
    *, transport: httpx.BaseTransport | None = None,
) -> OpenAI:
    def before_request(_: httpx.Request) -> None:
        budget.consume()

    client = stack.enter_context(httpx.Client(
        timeout=llm.timeout_seconds, follow_redirects=False, transport=transport,
        event_hooks={"request": [before_request]},
    ))
    return stack.enter_context(OpenAI(
        api_key=api_key, base_url=llm.base_url, timeout=llm.timeout_seconds,
        max_retries=0, http_client=client,
    ))


@dataclass(frozen=True, slots=True)
class RealRun:
    agent: EvalAgent
    details: dict[str, object]
    verify_final_corpus: Callable[[], None]


@contextmanager
def open_real_run(corpus: Sequence[CorpusDocument], budget: RequestBudget) -> Iterator[RealRun]:
    """Verify stores and local model files before constructing the paid client."""
    try:
        db = DatabaseSettings(_env_file=None)
        db_url = build_database_url(db)
        llm = LLMSettings(_env_file=None)
        documents = DocumentSettings(_env_file=None)
        qdrant = QdrantSettings(_env_file=None)
        embedding = EmbeddingSettings(_env_file=None)
        reranker = RerankerSettings(_env_file=None)
        rag = RAGSettings(_env_file=None)
    except (ValidationError, DatabaseConfigurationError, ValueError) as exc:
        raise EvalStop("invalid_configuration") from exc
    api_key = llm.api_key.get_secret_value().strip() if llm.api_key is not None else ""
    if not api_key or api_key == "your_api_key_here":
        raise EvalStop("invalid_credentials")
    if llm.base_url.rstrip("/") not in {"https://api.deepseek.com", "https://api.deepseek.com/v1"}:
        raise EvalStop("deepseek_endpoint_required")

    with ExitStack() as stack:
        engine = create_engine(
            db_url, isolation_level="REPEATABLE READ", execution_options={"postgresql_readonly": True},
            connect_args={"connect_timeout": 5},
        )
        stack.callback(engine.dispose)
        sessions = sessionmaker(bind=engine, expire_on_commit=False)
        client = QdrantClient(
            url=qdrant.build_url(), timeout=qdrant.timeout_seconds, prefer_grpc=False,
            check_compatibility=False,
        )
        stack.callback(client.close)
        vector_store = QdrantVectorStore(qdrant, client=client)
        preflight = partial(verify_corpus, corpus, documents.upload_dir, sessions, vector_store, client)
        snapshot = preflight()
        embedding_path, reranker_path = _model_paths(embedding, reranker)

        def guarded_bm25() -> tuple[BM25CorpusChunk, ...]:
            chunks = load_bm25_chunks(session_factory=sessions)
            if build_corpus_fingerprint(chunks) != snapshot.fingerprint:
                raise EvalStop("postgres_corpus_changed")
            return chunks

        retrieval = RerankedRetrievalService(
            HybridRetrievalService(
                RetrievalService(EmbeddingClient(embedding, snapshot_resolver=lambda _: embedding_path),
                                 vector_store),
                BM25Service(guarded_bm25),
            ),
            RerankerService(reranker, snapshot_resolver=lambda _: reranker_path),
        )
        checked_payloads = {chunk.chunk_id: _canonical_payload(_chunk_payload(chunk))
                            for chunk in snapshot.chunks}

        def guarded_search(question: str) -> RerankOutcome:
            outcome = retrieval.search(question)
            if any(_canonical_payload(_chunk_payload(chunk)) != checked_payloads.get(chunk.chunk_id)
                   for chunk in outcome.results):
                raise EvalStop("retrieval_corpus_changed")
            return outcome

        def verify_final() -> None:
            if preflight().fingerprint != snapshot.fingerprint:
                raise EvalStop("corpus_changed_during_run")

        sdk = _open_sdk(stack, llm, api_key, budget)
        agent = EvalAgent(
            LLMClient(llm, client=sdk), guarded_search, rag,
            catalog_factory=lambda: DocumentCatalogService(session_factory=sessions),
        )
        yield RealRun(agent, {
            "provider": "DeepSeek", "model": llm.model, "llm_sdk_retries": 0,
            "llm_timeout_seconds": llm.timeout_seconds, "ingestion_chunking": INGESTION_CHUNKING,
            "embedding_model": embedding.model_name, "embedding_revision": embedding.model_revision,
            "reranker_model": reranker.model_name, "reranker_revision": reranker.model_revision,
            "relevance_threshold": rag.min_relevance_score,
            "collection": qdrant.collection, "documents": list(snapshot.documents),
            "pg_chunk_count": len(snapshot.chunks), "qdrant_point_count": len(snapshot.chunks),
            "bm25_corpus_fingerprint": snapshot.fingerprint,
        }, verify_final)
