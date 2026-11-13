"""Opt-in, bounded full-RAG comparison in disposable PostgreSQL/Qdrant stores."""

from __future__ import annotations

import argparse
from collections.abc import Iterator, Sequence
from contextlib import ExitStack, contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from threading import Lock
from typing import Protocol
from uuid import uuid4

from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger
from qdrant_client import QdrantClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from backend.app.commands.index_document import index_document
from backend.app.core.config import (
    DatabaseSettings, EmbeddingSettings, LLMSettings, PROJECT_ROOT, QdrantSettings,
    RAGSettings, RerankerSettings,
)
from backend.app.core.database import Base, build_database_url
from backend.app.models.chunk import Chunk
from backend.app.models.document import Document
from backend.app.services.bm25 import BM25Service, load_bm25_chunks
from backend.app.services.document_catalog import DocumentCatalogService
from backend.app.services.document_parser import PageText, parse_document
from backend.app.services.embedding import (
    EmbeddingClient, SentenceEmbeddingModel, load_embedding_model, validate_model_input_length,
)
from backend.app.services.hybrid import HybridRetrievalService
from backend.app.services.llm import LLMClient
from backend.app.services.qdrant_store import QdrantVectorStore
from backend.app.services.reranker import RerankedRetrievalService, RerankerService
from backend.app.services.retrieval import RetrievalService
from backend.app.services.text_splitter import (
    CHUNK_SEPARATORS, ChunkDraft, _split_by_token_windows, split_pages,
)
from eval.agent import EvalAgent, EvalStop
from eval.chunk_comparison import _local_model_path, _pages
from eval.real import _model_paths, _open_sdk, verify_points
from eval.scoring import EvalInputs, load_inputs, score_observation


MAX_PAID_REQUESTS = 240
VARIANTS = ("o200k_200_40", "o200k_300_60", "bge_500_100")
_SAFE_NAME = re.compile(r"day19x_[0-9a-f]{16}\Z")


class BoundedBudget:
    """Hard cap across all variants, counted before each outbound HTTP request."""

    def __init__(self, limit: int) -> None:
        if type(limit) is not int or not 1 <= limit <= MAX_PAID_REQUESTS:
            raise ValueError("invalid paid request limit")
        self.limit = limit
        self.attempts = 0
        self._lock = Lock()

    def consume(self) -> None:
        with self._lock:
            if self.attempts >= self.limit:
                raise EvalStop("budget_exhausted")
            self.attempts += 1


class BGETokenizer(Protocol):
    def encode(
        self, text: str, *, add_special_tokens: bool, truncation: bool,
    ) -> Sequence[int]: ...


def split_bge_pages(pages: Sequence[PageText], tokenizer: BGETokenizer) -> list[ChunkDraft]:
    """Use production separators and fallback, with BGE's own token unit."""
    def token_length(content: str) -> int:
        return len(tokenizer.encode(content, add_special_tokens=True, truncation=False))

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500, chunk_overlap=100, length_function=token_length,
        separators=CHUNK_SEPARATORS, keep_separator="end",
    )
    drafts: list[ChunkDraft] = []
    for page in pages:
        if not page.text.strip():
            continue
        for content in splitter.split_text(page.text):
            for bounded, count in _split_by_token_windows(
                content, chunk_size=500, chunk_overlap=100, token_length=token_length,
            ):
                if bounded.strip():
                    drafts.append(ChunkDraft(
                        len(drafts), bounded, page.page,
                        {"chunk_size": 500, "chunk_overlap": 100, "length_unit": "bge_token",
                         "encoding_name": "bge-small-zh-v1.5", "token_count": count},
                    ))
    if not drafts:
        raise ValueError("BGE variant produced no chunks")
    return drafts


def build_drafts(
    inputs: EvalInputs, model: SentenceEmbeddingModel,
) -> dict[str, dict[str, list[ChunkDraft]]]:
    """Verify frozen inputs and reject every oversized model passage before writes."""
    pages_by_file = _pages(Path(__file__).resolve().parent, inputs.corpus)
    drafts: dict[str, dict[str, list[ChunkDraft]]] = {}
    for label in VARIANTS:
        per_file: dict[str, list[ChunkDraft]] = {}
        for filename, pages in pages_by_file.items():
            if label == "bge_500_100":
                chunks = split_bge_pages(pages, model.tokenizer)
            else:
                size, overlap = (200, 40) if label == "o200k_200_40" else (300, 60)
                chunks = split_pages(
                    pages, chunk_size=size, chunk_overlap=overlap, encoding_name="o200k_base",
                )
            for chunk in chunks:
                validate_model_input_length(model, chunk.content)
            per_file[filename] = chunks
        drafts[label] = per_file
    return drafts


@dataclass(slots=True)
class VariantRun:
    label: str
    schema: str
    collection: str
    sessions: sessionmaker[Session]
    search: RerankedRetrievalService
    chunk_count: int


@contextmanager
def isolated_variant(
    label: str, inputs: EvalInputs, drafts: dict[str, list[ChunkDraft]],
    embedding: EmbeddingClient, reranker: RerankerService,
) -> Iterator[VariantRun]:
    """Create only unique experiment resources, then remove only those resources."""
    suffix = uuid4().hex[:16]
    name = f"day19x_{suffix}"
    if not _SAFE_NAME.fullmatch(name):
        raise ValueError("invalid experiment identity")
    db = DatabaseSettings(_env_file=None)
    url = build_database_url(db)
    admin = create_engine(url, connect_args={"connect_timeout": 5})
    scoped: Engine | None = None
    client: QdrantClient | None = None
    schema_created = False
    collection_created = False
    try:
        with admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{name}"'))
        schema_created = True
        scoped = create_engine(
            url, connect_args={"connect_timeout": 5, "options": f"-csearch_path={name}"},
        )
        with scoped.connect() as connection:
            if connection.execute(text("select current_schema() ")).scalar_one() != name:
                raise RuntimeError("experiment schema isolation failed")
        Base.metadata.create_all(scoped, tables=[Document.__table__, Chunk.__table__])
        sessions = sessionmaker(scoped, expire_on_commit=False)

        qdrant = QdrantSettings(_env_file=None, collection=name)
        client = QdrantClient(
            url=qdrant.build_url(), timeout=qdrant.timeout_seconds,
            check_compatibility=False,
        )
        if client.collection_exists(name):
            raise RuntimeError("experiment collection already exists")
        store = QdrantVectorStore(qdrant, client=client)
        store.initialize_collection()
        collection_created = True

        ids = []
        with sessions() as session:
            for source in inputs.corpus:
                pdf = Path(__file__).resolve().parent / "corpus" / source.filename
                document = Document(
                    id=uuid4(), filename=source.filename, size=pdf.stat().st_size,
                    status="ready", extracted_text="\f".join(page.text for page in parse_document(
                        pdf, ".pdf", max_pdf_pages=500, read_chunk_size=1024 * 1024,
                    )),
                )
                session.add(document)
                session.flush()
                for draft in drafts[source.filename]:
                    session.add(Chunk(
                        chunk_id=uuid4(), doc_id=document.id, chunk_index=draft.chunk_index,
                        content=draft.content, page=draft.page,
                        chunk_metadata=dict(draft.metadata),
                    ))
                ids.append(document.id)
            session.commit()
        for document_id in ids:
            index_document(
                document_id, session_factory=sessions,
                embedding_client_factory=lambda: embedding,
                vector_store_factory=lambda: store,
            )
        saved = load_bm25_chunks(session_factory=sessions)
        expected_count = sum(len(chunks) for chunks in drafts.values())
        if len(saved) != expected_count:
            raise RuntimeError("experiment PostgreSQL count mismatch")
        points, offset = client.scroll(
            collection_name=name, limit=expected_count + 1,
            with_payload=True, with_vectors=False,
        )
        verify_points(saved, points, has_more=offset is not None)
        search = RerankedRetrievalService(
            HybridRetrievalService(
                RetrievalService(embedding, store),
                BM25Service(lambda: load_bm25_chunks(session_factory=sessions)),
            ), reranker,
        )
        yield VariantRun(label, name, name, sessions, search, expected_count)
    finally:
        if client is not None:
            try:
                if collection_created:
                    client.delete_collection(name)
            except Exception as exc:
                print(f"cleanup_qdrant_failed={type(exc).__name__}")
            finally:
                client.close()
        if scoped is not None:
            scoped.dispose()
        try:
            if schema_created:
                with admin.begin() as connection:
                    connection.execute(text(f'DROP SCHEMA "{name}" CASCADE'))
        except Exception as exc:
            print(f"cleanup_postgres_failed={type(exc).__name__}")
        finally:
            admin.dispose()


def run(*, allow_paid: bool, max_requests: int, max_cases: int = 50) -> dict[str, object]:
    """Run identical frozen questions through three isolated production RAG chains."""
    logger.remove()
    if not allow_paid and max_requests != MAX_PAID_REQUESTS:
        raise ValueError("request limit applies only to paid runs")
    budget = BoundedBudget(max_requests)
    inputs = load_inputs(Path(__file__).resolve().parent)
    if not 1 <= max_cases <= len(inputs.cases):
        raise ValueError("invalid question count")
    embedding_settings = EmbeddingSettings(_env_file=None)
    reranker_settings = RerankerSettings(_env_file=None)
    embedding_path, reranker_path = _model_paths(embedding_settings, reranker_settings)
    model = load_embedding_model(embedding_path, embedding_settings)
    drafts = build_drafts(inputs, model)
    embedding = EmbeddingClient(
        embedding_settings, snapshot_resolver=lambda _: embedding_path,
        model_loader=lambda _path, _settings: model,
    )
    reranker = RerankerService(
        reranker_settings, snapshot_resolver=lambda _: reranker_path,
    )
    llm = LLMSettings(_env_file=None)
    key = llm.api_key.get_secret_value().strip() if llm.api_key is not None else ""
    if allow_paid and (not key or key == "your_api_key_here"):
        raise ValueError("paid API key unavailable")
    if llm.base_url.rstrip("/") not in {"https://api.deepseek.com", "https://api.deepseek.com/v1"}:
        raise ValueError("official DeepSeek endpoint required")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    output_dir = PROJECT_ROOT / "data" / "eval" / "day19_full_comparison" / run_id
    results: dict[str, list[dict[str, object]]] = {label: [] for label in VARIANTS}
    with ExitStack() as stack:
        variants = {
            label: stack.enter_context(isolated_variant(label, inputs, drafts[label], embedding, reranker))
            for label in VARIANTS
        }
        for label, variant in variants.items():
            outcome = variant.search.search(inputs.cases[0].question)
            print(f"preflight={label} chunks={variant.chunk_count} retrieved={len(outcome.results)}")
        if not allow_paid:
            return {"status": "preflight_only", "paid_requests": 0,
                    "chunk_counts": {label: variant.chunk_count for label, variant in variants.items()}}

        output_dir.mkdir(parents=True, exist_ok=False)
        sdk = _open_sdk(stack, llm, key, budget)  # type: ignore[arg-type]
        llm_client = LLMClient(llm, client=sdk)
        rag = RAGSettings(_env_file=None)
        agents = {
            label: EvalAgent(
                llm_client, variant.search.search, rag,
                catalog_factory=lambda sessions=variant.sessions: DocumentCatalogService(
                    session_factory=sessions,
                ),
            )
            for label, variant in variants.items()
        }
        with (output_dir / "results.jsonl").open("w", encoding="utf-8") as output:
            for index, case in enumerate(inputs.cases[:max_cases]):
                order = VARIANTS[index % len(VARIANTS):] + VARIANTS[:index % len(VARIANTS)]
                for label in order:
                    observation = agents[label].run(case.question)
                    row = asdict(score_observation(case, observation))
                    row["variant"] = label
                    results[label].append(row)
                    output.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
                    output.flush()
                    print(f"case={case.id} variant={label} status={row['status']} requests={budget.attempts}")
                    if observation.stop_run or observation.error_code is not None:
                        break
                if any(rows and rows[-1]["status"] == "error" for rows in results.values()):
                    break

    complete = max_cases == len(inputs.cases) and all(
        len(rows) == len(inputs.cases) for rows in results.values()
    )
    summary: dict[str, object] = {
        "status": "complete" if complete else "incomplete", "run_id": run_id,
        "model_alias": llm.model, "paid_requests": budget.attempts,
        "requested_cases": max_cases,
        "corpus_variant": "day17-v1", "dataset_variant": "day17-v1.1",
        "note": "bge_500_100 is a new BGE-token variant, not the original o200k 500/100",
        "variants": {},
    }
    for label, rows in results.items():
        answerable = [row for row in rows if row["source_hit"] is not None]
        summary["variants"][label] = {
            "completed_cases": len(rows), "errors": sum(row["status"] == "error" for row in rows),
            "source_hit_numerator": sum(row["source_hit"] is True for row in answerable),
            "source_hit_denominator": 40 if complete else None,
            "candidate_hit_numerator": sum(row["candidate_source_hit"] is True for row in answerable),
        }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    """Default to no paid requests; explicit flag and bounded cap are required."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-paid", action="store_true")
    parser.add_argument("--max-requests", type=int, default=MAX_PAID_REQUESTS)
    parser.add_argument("--max-cases", type=int, default=50)
    args = parser.parse_args(argv)
    if not 1 <= args.max_requests <= MAX_PAID_REQUESTS:
        parser.error("max-requests must be between 1 and 240")
    try:
        result = run(
            allow_paid=args.allow_paid, max_requests=args.max_requests,
            max_cases=args.max_cases,
        )
    except Exception as exc:
        print(f"experiment_failed={type(exc).__name__}")
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
