"""Offline Day 18 regressions for the frozen evaluation contract."""

from collections.abc import Iterator, Sequence
from contextlib import ExitStack, contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import httpx
import pytest
from qdrant_client import models
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import LLMSettings, RAGSettings
from backend.app.core.database import Base
from backend.app.models.chunk import Chunk
from backend.app.models.document import Document
from backend.app.services.document_catalog import DocumentListItem, DocumentListResult
from backend.app.services.document_parser import parse_document, serialize_pages
from backend.app.services.llm import AgentToolCall, LLMClient, LLMMessage, LLMServiceError, LLMToolDefinition
from backend.app.services.rag import NO_RELEVANT_KNOWLEDGE, RAGAnswer, RAGSource
from backend.app.services.reranker import RerankOutcome, RerankedChunk
from eval import eval as runner
from eval import real
from eval.agent import Candidate, EvalAgent, EvalStop, Observation, RequestBudget, SEARCH_TOOL
from eval.scoring import EvalInputs, InputError, load_inputs, score_observation


@pytest.fixture(autouse=True)
def isolated_conversation_dependency() -> None:
    """The evaluator calls the graph without the HTTP/conversation layer."""


@pytest.fixture(scope="module")
def inputs() -> EvalInputs:
    return load_inputs(runner.EVAL_DIR)


def _answer(text: str, *sources: tuple[str, int], tool: str = SEARCH_TOOL) -> Observation:
    return Observation(
        RAGAnswer(text, "stub", tuple(RAGSource(*source) for source in sources)), tool, (), 10.0,
    )


def _rows(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


@pytest.mark.parametrize("problem", ["missing_case", "duplicate_case", "wrong_version", "missing_rule", "pdf"])
def test_bad_frozen_input_rejected(monkeypatch: pytest.MonkeyPatch, problem: str) -> None:
    original = Path.read_bytes

    def read(path: Path) -> bytes:
        data = original(path)
        if path.name == "eval_dataset.jsonl" and problem in {"missing_case", "duplicate_case"}:
            lines = data.splitlines(keepends=True)
            return b"".join(lines[:-1] if problem == "missing_case" else lines[:-1] + lines[:1])
        if path.name == "answer_rubric.json" and problem in {"wrong_version", "missing_rule"}:
            rubric = json.loads(data)
            if problem == "wrong_version":
                rubric["dataset_version"] = "day17-v1"
            else:
                del rubric["cases"]["qa_001"]
            return json.dumps(rubric).encode()
        if path.name == "earthquake.pdf" and problem == "pdf":
            return data + b"\x00"
        return data

    monkeypatch.setattr(Path, "read_bytes", read)
    with pytest.raises(InputError):
        load_inputs(runner.EVAL_DIR)


@pytest.mark.parametrize(
    ("number", "answer", "passed"),
    [
        (1, "待在床上，拿枕头盖住头和脖子。", True),
        (1, "不要留在床上，用枕头保护头部和颈部。", False),
        (5, "约15.24厘米。", True),
        (5, "不是六英寸，而是七英寸。", False),
        (10, "必须在户外运行。", True),
        (10, "发电机只能在室外使用，也可以在室内使用。", False),
        (12, "低于 35 摄氏度。", True),
        (12, "低于 95 摄氏度。", False),
        (15, "与门窗至少保持 6.096 米。", True),
        (15, "与开口保持 20 英尺以内。", False),
        (20, "可能引发海啸，应立即往内陆撤。", False),
        (28, "强风和洪水。未进水时去最低层内侧，进水时到最高层，避免进入封闭阁楼。", True),
        (28, "强风和洪水。进水时到最低层内侧，未进水时去最高层，避免进入封闭阁楼。", False),
    ],
)
def test_keyword_rules(inputs: EvalInputs, number: int, answer: str, passed: bool) -> None:
    case = inputs.cases[number - 1]
    result = score_observation(case, _answer(answer, *case.expected_sources))
    assert result.answer_pass is passed


def test_sources_are_all_required_and_distinct_from_answer_score(inputs: EvalInputs) -> None:
    case = inputs.cases[38]
    first, second, third = case.expected_sources
    partial = score_observation(case, _answer(case.expected_answer, second, first, first, ("flood.pdf", 2)))
    assert partial.answer_pass
    assert partial.source_hit is False
    assert partial.source_coverage == pytest.approx(2 / 3)
    assert score_observation(case, _answer(case.expected_answer, third, second, first, first)).source_hit is True


def test_refusal_and_errors_have_separate_denominators(inputs: EvalInputs) -> None:
    fact, failed, refusal, unrun = (inputs.cases[index] for index in (0, 1, 40, 41))
    error = score_observation(failed, Observation(None, SEARCH_TOOL, (), 20, "upstream_timeout"))
    refused = score_observation(refusal, _answer(NO_RELEVANT_KNOWLEDGE))
    bad_route = score_observation(refusal, _answer(NO_RELEVANT_KNOWLEDGE, tool="list_documents"))
    bad_citation = score_observation(refusal, _answer(NO_RELEVANT_KNOWLEDGE, ("flood.pdf", 1)))
    assert not bad_route.answer_pass and bad_route.tool_mismatch
    assert bad_citation.refused and not bad_citation.answer_pass
    assert error.source_hit is error.candidate_source_hit is None
    assert error.refused is None and not error.answer_pass
    assert refused.source_hit is refused.candidate_source_hit is None
    summary = runner.summarize(
        [score_observation(fact, _answer(fact.expected_answer, *fact.expected_sources)), error, refused],
        [fact, failed, refusal, unrun],
    )
    assert summary.accuracy == summary.coverage == runner.Rate(2, 4)
    assert summary.source_hit == summary.joint_pass == summary.correct_refusal == runner.Rate(1, 2)
    assert (summary.execution_errors, summary.not_run, summary.quality_failures) == (1, 1, 0)
    assert (summary.first_ms, summary.warm_p50_ms, summary.warm_p95_ms) == (10, 15, 20)


class _StubLLM:
    model = "stub"

    def __init__(self, generated: str | BaseException) -> None:
        self.generated = generated
        self.generations = 0

    def select_tool(
        self, messages: Sequence[LLMMessage], tools: Sequence[LLMToolDefinition],
    ) -> AgentToolCall:
        question = messages[-1]["content"]
        if question == "目录":
            return {"call_id": "list", "name": "list_documents", "arguments": {}}
        return {"call_id": "search", "name": SEARCH_TOOL, "arguments": {"query": question}}

    def complete_messages(self, messages: Sequence[LLMMessage]) -> str:
        self.generations += 1
        if isinstance(self.generated, BaseException):
            raise self.generated
        return self.generated


def _chunk(filename: str, page: int, rank: int, vector_score: float) -> RerankedChunk:
    return RerankedChunk(
        uuid4(), uuid4(), rank - 1, "offline fixture", page, filename, {}, 1.0, 0.03,
        rank, rank, 0, vector_score, rank, None,
    )


def _catalog() -> SimpleNamespace:
    document = DocumentListItem(uuid4(), "catalog.txt", 10, "ready", datetime.now(timezone.utc))
    return SimpleNamespace(list_documents=lambda: DocumentListResult((document,), False))


def test_same_call_capture_gate_tool_mismatch_and_reset(inputs: EvalInputs) -> None:
    case = inputs.cases[0]
    low = _chunk("earthquake.pdf", 2, 1, 0.2)
    high = _chunk("flood.pdf", 1, 2, 0.8)
    questions = []
    llm = _StubLLM(case.expected_answer)
    ticks = iter([1, 1.125, 2, 2.25, 3, 3.5])

    def search(question: str) -> RerankOutcome:
        questions.append(question)
        chunks = () if question == "无候选" else (low, high)
        return RerankOutcome(chunks, (), len(chunks), 0)

    agent = EvalAgent(llm, search, RAGSettings(_env_file=None, min_relevance_score=0.46,
                                               min_reranker_score=None),
                      catalog_factory=_catalog, clock=lambda: next(ticks))
    observed = agent.run(case.question)
    scored = score_observation(case, observed)
    assert scored.answer_pass and scored.candidate_source_hit is True and scored.source_hit is False
    assert observed.latency_ms == 125
    assert observed.retrieved_chunks == (
        Candidate(str(low.chunk_id), "earthquake.pdf", 2, 1, False, 0.2, 1.0),
        Candidate(str(high.chunk_id), "flood.pdf", 1, 2, True, 0.8, 1.0),
    )
    assert observed.answer.sources == (RAGSource("flood.pdf", 1),)
    wrong = score_observation(case, agent.run("目录"))
    assert wrong.answer == case.expected_answer and wrong.tool_mismatch and not wrong.answer_pass
    assert wrong.retrieved_chunks is None and wrong.sources == ()
    empty = agent.run("无候选")
    assert empty.retrieved_chunks == () and empty.answer.answer == NO_RELEVANT_KNOWLEDGE
    assert questions == [case.question, "无候选"]
    assert llm.generations == 2


@pytest.mark.parametrize(
    ("failure", "code", "stop"),
    [
        (TimeoutError("upstream"), "upstream_timeout", False),
        (LLMServiceError("generation"), "generation_failed", False),
        (KeyboardInterrupt(), "interrupted", True),
    ],
)
def test_attempt_errors_keep_captured_evidence(failure: BaseException, code: str, stop: bool) -> None:
    chunk = _chunk("flood.pdf", 2, 1, 0.8)
    agent = EvalAgent(
        _StubLLM(failure), lambda _: RerankOutcome((chunk,), (), 1, 0),
        RAGSettings(_env_file=None, min_relevance_score=0.46), catalog_factory=_catalog,
    )
    result = agent.run("洪水")
    assert result.answer is None and result.error_code == code and result.stop_run is stop
    assert result.selected_tool == SEARCH_TOOL and result.retrieved_chunks[0].chunk_id == str(chunk.chunk_id)


@pytest.mark.parametrize("args", [[], ["--allow-paid"], ["--max-llm-requests", "100"],
                                  ["--allow-paid", "--max-llm-requests", "101"]])
def test_cli_rejects_unauthorized_real_before_preflight(
    monkeypatch: pytest.MonkeyPatch, args: list[str],
) -> None:
    monkeypatch.setattr(runner, "load_inputs", lambda *_: pytest.fail("preflight must not run"))
    with pytest.raises(SystemExit) as exit_info:
        runner.main(["--mode", "real", *args])
    assert exit_info.value.code == 2


@pytest.mark.parametrize("limit", [1, 2])
def test_real_budget_stops_and_keeps_attempted_rows(
    inputs: EvalInputs, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, limit: int,
) -> None:
    sent = []

    @contextmanager
    def open_fake_run(corpus: object, budget: RequestBudget) -> Iterator[real.RealRun]:
        def run(question: str) -> Observation:
            try:
                budget.consume()
                sent.append(question)
                budget.consume()
                sent.append(question)
            except EvalStop as exc:
                return Observation(None, SEARCH_TOOL, (), 1, exc.code, True)
            return _answer(NO_RELEVANT_KNOWLEDGE)

        yield real.RealRun(SimpleNamespace(run=run), {"model": "stub"}, lambda: None)

    monkeypatch.setattr(real, "open_real_run", open_fake_run)
    formal = tmp_path / "formal.md"
    outcome = runner.run_evaluation(inputs, mode="real", allow_paid=True, max_llm_requests=limit,
                                    output_root=tmp_path, formal_report=formal)
    rows = _rows(outcome.directory / "eval_results.jsonl")
    assert len(rows) == 1 and rows[0]["id"] == "qa_001"
    assert rows[0]["status"] == ("error" if limit == 1 else "ok")
    assert outcome.metadata.status == "incomplete"
    assert outcome.metadata.stop_reason == "budget_exhausted"
    assert outcome.metadata.llm_attempts == len(sent) == limit
    assert outcome.summary.not_run == 49
    assert not formal.exists()


@pytest.mark.parametrize(
    ("failure", "code", "stop"),
    [("budget", "budget_exhausted", True), ("auth", "invalid_credentials", True),
     ("timeout", "upstream_timeout", False)],
)
def test_sdk_budget_counts_actual_attempts_without_retries(failure: str, code: str, stop: bool) -> None:
    requests = []

    def send(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if failure == "auth":
            return httpx.Response(401, json={"error": {"message": "fake auth failure"}})
        if failure == "timeout":
            raise httpx.ReadTimeout("fake timeout", request=request)
        return httpx.Response(200, json={
            "id": "offline", "object": "chat.completion", "created": 0, "model": "stub",
            "choices": [{"index": 0, "finish_reason": "tool_calls", "message": {
                "role": "assistant", "content": None,
                "tool_calls": [{"id": "search", "type": "function", "function": {
                    "name": SEARCH_TOOL, "arguments": json.dumps({"query": "洪水"}),
                }}],
            }}],
        })

    budget = RequestBudget(1)
    settings = LLMSettings(
        _env_file=None, api_key="offline-fixture", base_url="https://api.deepseek.com",
        model="stub", timeout_seconds=2, extra_body={},
    )
    chunk = _chunk("flood.pdf", 2, 1, 0.8)
    with ExitStack() as stack:
        sdk = real._open_sdk(stack, settings, "offline-fixture", budget, transport=httpx.MockTransport(send))
        agent = EvalAgent(
            LLMClient(settings, client=sdk), lambda _: RerankOutcome((chunk,), (), 1, 0),
            RAGSettings(_env_file=None, min_relevance_score=0.46), catalog_factory=_catalog,
        )
        result = agent.run("洪水")
    assert len(requests) == budget.attempts == 1
    assert result.error_code == code and result.stop_run is stop
    if failure == "budget":
        assert result.selected_tool == SEARCH_TOOL and len(result.retrieved_chunks) == 1


def test_interruption_retains_completed_rows(
    inputs: EvalInputs, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    def run(question: str) -> Observation:
        if question == inputs.cases[0].question:
            return _answer(NO_RELEVANT_KNOWLEDGE)
        raise KeyboardInterrupt()

    monkeypatch.setattr(runner, "_mock_agent", lambda _: SimpleNamespace(model="stub", run=run))
    outcome = runner.run_evaluation(inputs, mode="mock", output_root=tmp_path)
    assert outcome.metadata.stop_reason == "interrupted"
    assert outcome.summary.not_run == 49
    assert [row["id"] for row in _rows(outcome.directory / "eval_results.jsonl")] == ["qa_001"]


def test_mock_run_is_recomputable_and_preserves_formal_report(inputs: EvalInputs, tmp_path: Path) -> None:
    formal = tmp_path / "eval_report.md"
    formal.write_text("existing baseline", encoding="utf-8")
    outcome = runner.run_evaluation(inputs, mode="mock", output_root=tmp_path, formal_report=formal)
    assert outcome.metadata.status == "complete" and outcome.metadata.llm_attempts == 0
    assert formal.read_text(encoding="utf-8") == "existing baseline"
    assert "模拟诊断" in (outcome.directory / "eval_report.md").read_text(encoding="utf-8")
    rows = _rows(outcome.directory / "eval_results.jsonl")
    assert [row["id"] for row in rows] == [case.id for case in inputs.cases]
    assert all(row["status"] == "ok" for row in rows)
    assert all("content" not in chunk for row in rows for chunk in row["retrieved_chunks"])
    assert outcome.summary.accuracy == runner.Rate(sum(row["answer_pass"] for row in rows), 50)
    assert outcome.summary.source_hit == runner.Rate(sum(row["source_hit"] is True for row in rows), 40)
    assert outcome.summary.correct_refusal == runner.Rate(sum(row["answer_pass"] for row in rows[40:]), 10)
    assert rows[0]["candidate_source_hit"] is True and rows[0]["source_hit"] is False
    assert rows[31]["source_coverage"] == 0.5


FrozenCorpusStores = tuple[sessionmaker[Session], list[models.Record], SimpleNamespace, SimpleNamespace]
FROZEN_CHUNK_SPANS: dict[str, tuple[tuple[int, int, int, int], ...]] = {
    # page, text offset, character length, token count from the Day 17 300/60 import.
    "earthquake.pdf": ((1, 0, 657, 183), (2, 0, 1291, 296),
                       (2, 1091, 1178, 294), (2, 2034, 521, 127)),
    "flood.pdf": ((1, 0, 1120, 300), (1, 918, 423, 115),
                  (2, 0, 1288, 291), (2, 1054, 1232, 298), (2, 2053, 1018, 244)),
    "hurricane.pdf": ((1, 0, 969, 246), (2, 0, 1347, 292),
                      (2, 1104, 1320, 295), (2, 2202, 1334, 297),
                      (2, 3296, 1318, 292)),
    "tornado.pdf": ((1, 0, 812, 213), (2, 0, 1262, 294),
                    (2, 1006, 1252, 295), (2, 2025, 353, 89)),
    "wildfire.pdf": ((1, 0, 738, 201), (2, 0, 1252, 291),
                     (2, 1063, 1193, 286)),
    "winter-storm.pdf": ((1, 0, 693, 183), (2, 0, 1298, 297),
                         (2, 1085, 1136, 297), (2, 2040, 693, 188)),
}


@pytest.fixture
def frozen_corpus_stores(inputs: EvalInputs, tmp_path: Path) -> Iterator[FrozenCorpusStores]:
    """Build local stores from frozen PDFs and verified Day 17 300/60 spans."""
    engine = create_engine("sqlite://")
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    points: list[models.Record] = []
    try:
        Base.metadata.create_all(engine)
        with sessions.begin() as session:
            for pdf in inputs.corpus:
                doc_id = uuid4()
                pdf_path = runner.EVAL_DIR / "corpus" / pdf.filename
                content = pdf_path.read_bytes()
                (tmp_path / f"{doc_id}.pdf").write_bytes(content)
                pages = parse_document(pdf_path, ".pdf", max_pdf_pages=pdf.page_count,
                                       read_chunk_size=65536)
                spans = FROZEN_CHUNK_SPANS[pdf.filename]
                assert len(spans) == real.CHUNKS_PER_PDF[pdf.filename]
                session.add(Document(id=doc_id, filename=pdf.filename, size=len(content),
                                     status="ready", extracted_text=serialize_pages(pages)))
                session.flush()
                for index, (page_number, start, length, token_count) in enumerate(spans):
                    page_text = pages[page_number - 1].text
                    assert start >= 0 and start + length <= len(page_text)
                    chunk_content = page_text[start:start + length]
                    assert chunk_content.strip()
                    metadata = {**real.INGESTION_CHUNKING, "length_unit": "token",
                                "token_count": token_count}
                    chunk_id = uuid4()
                    session.add(Chunk(chunk_id=chunk_id, doc_id=doc_id, chunk_index=index,
                                      content=chunk_content, page=page_number,
                                      chunk_metadata=metadata))
                    points.append(models.Record(id=str(chunk_id), payload={
                        "chunk_id": str(chunk_id), "doc_id": str(doc_id), "filename": pdf.filename,
                        "chunk_index": index, "page": page_number,
                        "content": chunk_content, "metadata": metadata,
                    }))
        client = SimpleNamespace(scroll=lambda **_: (points, None))
        store = SimpleNamespace(settings=SimpleNamespace(collection="fixture"), validate_collection=lambda: None)
        yield sessions, points, client, store
    finally:
        engine.dispose()


def test_real_preflight_checks_both_store_identities(
    inputs: EvalInputs, tmp_path: Path, frozen_corpus_stores: FrozenCorpusStores,
) -> None:
    sessions, points, client, store = frozen_corpus_stores
    snapshot = real.verify_corpus(inputs.corpus, tmp_path, sessions, store, client)
    assert len(snapshot.chunks) == len(points) == 25
    points.append(models.Record(id=str(uuid4()), payload={}))
    with pytest.raises(EvalStop, match="qdrant_corpus_mismatch"):
        real.verify_corpus(inputs.corpus, tmp_path, sessions, store, client)
    points.pop()
    assert isinstance(points[0].payload, dict)
    points[0].payload["page"] = 2
    with pytest.raises(EvalStop, match="qdrant_payload_mismatch"):
        real.verify_corpus(inputs.corpus, tmp_path, sessions, store, client)
    with sessions.begin() as session:
        session.add(Document(filename="extra.pdf", size=10, status="ready", extracted_text="other"))
    with pytest.raises(EvalStop, match="postgres_corpus_mismatch"):
        real.verify_corpus(inputs.corpus, tmp_path, sessions, store, client)


def test_real_preflight_rejects_matching_stores_with_chunk_text_not_in_frozen_pdf(
    inputs: EvalInputs, tmp_path: Path, frozen_corpus_stores: FrozenCorpusStores,
) -> None:
    sessions, points, client, store = frozen_corpus_stores
    point = points[0]
    assert isinstance(point.payload, dict)
    incorrect_content = "This sentence is not in the frozen PDF."
    assert point.payload["content"] != incorrect_content
    source_pdf = runner.EVAL_DIR / "corpus" / str(point.payload["filename"])
    source_pages = parse_document(source_pdf, ".pdf", max_pdf_pages=2, read_chunk_size=65536)
    assert all(incorrect_content not in page.text for page in source_pages)
    point.payload["content"] = incorrect_content
    with sessions.begin() as session:
        chunk = session.get(Chunk, UUID(str(point.id)))
        assert chunk is not None
        chunk.content = incorrect_content

    with pytest.raises(EvalStop, match="postgres_chunks_mismatch"):
        real.verify_corpus(inputs.corpus, tmp_path, sessions, store, client)
