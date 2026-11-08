"""Validate the frozen inputs and score answers, candidates and citations separately."""

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
import unicodedata

from backend.app.services.rag import NO_RELEVANT_KNOWLEDGE, RAGSource
from eval.agent import Candidate, Observation, SEARCH_TOOL

DATASET_VERSION = "day17-v1.1"
CORPUS_VERSION = "day17-v1"
RUBRIC_VERSION = "day18-rubric-v1"
DATASET_SHA256 = "3cc6403145de583fc634fe0683fb99ecc842e86be9b4181aeb089d63bacedbfa"
MANIFEST_SHA256 = "1b7e51c6bff6c9f5496cef59f7d0489220d24bd60363c10ff4a302285ebe79b8"
CATEGORY_COUNTS = {"simple_fact": 18, "cross_paragraph": 12, "multi_hop": 10, "unanswerable": 10}
DIFFICULTY_COUNTS = {"easy": 15, "medium": 20, "hard": 15}
_CASE_FIELDS = {"id", "category", "question", "expected_answer", "expected_source", "difficulty"}

SourceKey = tuple[str, int]


class InputError(ValueError):
    """An invalid or modified evaluation input."""


@dataclass(frozen=True, slots=True)
class CorpusDocument:
    filename: str
    sha256: str
    page_count: int


@dataclass(frozen=True, slots=True)
class FactGroup:
    id: str
    any_of: tuple[re.Pattern[str], ...]
    none_of: tuple[re.Pattern[str], ...] = ()

    def matches(self, answer: str) -> bool:
        """Match one acceptable expression and reject explicit contradictions."""
        return (any(pattern.search(answer) for pattern in self.any_of)
                and not any(pattern.search(answer) for pattern in self.none_of))


@dataclass(frozen=True, slots=True)
class EvalCase:
    id: str
    category: str
    difficulty: str
    question: str
    expected_answer: str
    expected_sources: tuple[SourceKey, ...]
    fact_groups: tuple[FactGroup, ...]


@dataclass(frozen=True, slots=True)
class EvalInputs:
    cases: tuple[EvalCase, ...]
    corpus: tuple[CorpusDocument, ...]
    rubric_sha256: str


@dataclass(frozen=True, slots=True)
class EvalResult:
    id: str
    category: str
    difficulty: str
    status: str
    error_code: str | None
    selected_tool: str | None
    tool_mismatch: bool | None
    answer: str | None
    sources: tuple[RAGSource, ...] | None
    retrieved_chunks: tuple[Candidate, ...] | None
    candidate_source_hit: bool | None
    source_hit: bool | None
    candidate_source_coverage: float | None
    source_coverage: float | None
    answer_pass: bool
    missing_fact_groups: tuple[str, ...] | None
    refused: bool | None
    latency_ms: float
    stop_run: bool


def _normalized(value: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", value).casefold())


def _text_bytes(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n")


def _unique_object(items: list[tuple[str, object]]) -> dict[str, object]:
    result = {}
    for key, value in items:
        if key in result:
            raise InputError("JSON 输入包含重复字段")
        result[key] = value
    return result


def _patterns(value: object) -> tuple[re.Pattern[str], ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise InputError("评分规则必须使用非空正则表达式字符串")
    return tuple(re.compile(pattern) for pattern in value)


def _fact_groups(value: object) -> tuple[FactGroup, ...]:
    if not isinstance(value, list) or not value:
        raise InputError("每道有答案题必须提供事实组")
    groups = []
    for group in value:
        if not isinstance(group, dict) or not {"id", "any_of"} <= group.keys() <= {"id", "any_of", "none_of"}:
            raise InputError("事实组字段不符合约定")
        group_id = group["id"]
        patterns = _patterns(group["any_of"])
        if not isinstance(group_id, str) or not group_id.strip() or not patterns:
            raise InputError("事实组必须具有名称和至少一条匹配规则")
        groups.append(FactGroup(group_id, patterns, _patterns(group.get("none_of", []))))
    if len({group.id for group in groups}) != len(groups):
        raise InputError("同一道题的事实组名称重复")
    return tuple(groups)


def _load_rubric(content: bytes, answerable_ids: set[str]) -> dict[str, tuple[FactGroup, ...]]:
    rubric = json.loads(content, object_pairs_hook=_unique_object)
    if (not isinstance(rubric, dict) or set(rubric) != {"version", "dataset_version", "cases"}
            or rubric["version"] != RUBRIC_VERSION or rubric["dataset_version"] != DATASET_VERSION):
        raise InputError("评分规则版本与冻结题集不匹配")
    cases = rubric["cases"]
    if not isinstance(cases, dict) or set(cases) != answerable_ids:
        raise InputError("评分规则必须恰好覆盖 40 道有答案题")
    return {case_id: _fact_groups(groups) for case_id, groups in cases.items()}


def _load_corpus(root: Path, manifest_bytes: bytes) -> tuple[CorpusDocument, ...]:
    if sha256(manifest_bytes).hexdigest() != MANIFEST_SHA256:
        raise InputError("冻结语料清单的 SHA-256 不匹配")
    manifest = json.loads(manifest_bytes)
    corpus = tuple(CorpusDocument(item["filename"], item["sha256"], item["page_count"])
                   for item in manifest["documents"])
    for document in corpus:
        pdf = (root / "corpus" / document.filename).read_bytes()
        if sha256(pdf).hexdigest() != document.sha256:
            raise InputError(f"冻结 PDF 的 SHA-256 不匹配（{document.filename}）")
    return corpus


def _load_cases(
    data: bytes, rubric: bytes, corpus: Sequence[CorpusDocument],
) -> tuple[EvalCase, ...]:
    if sha256(data).hexdigest() != DATASET_SHA256:
        raise InputError(f"题集 SHA-256 与 {DATASET_VERSION} 不匹配")
    rows = [json.loads(line, object_pairs_hook=_unique_object) for line in data.decode("utf-8").splitlines()]
    if ([row["id"] for row in rows] != [f"qa_{number:03d}" for number in range(1, 51)]
            or any(set(row) != _CASE_FIELDS for row in rows)
            or Counter(row["category"] for row in rows) != CATEGORY_COUNTS
            or Counter(row["difficulty"] for row in rows) != DIFFICULTY_COUNTS):
        raise InputError("题号、字段或分布与冻结题集不匹配")
    questions = {_normalized(row["question"]) for row in rows}
    if len(questions) != len(rows) or "" in questions:
        raise InputError("题集含空白或重复问题")
    answerable_ids = {row["id"] for row in rows if row["category"] != "unanswerable"}
    rules = _load_rubric(rubric, answerable_ids)
    pages = {item.filename: item.page_count for item in corpus}
    cases = []
    for row in rows:
        case_id = row["id"]
        sources = row["expected_source"]
        if not isinstance(sources, list) or any(
            not isinstance(source, dict) or set(source) != {"filename", "page"}
            or source["filename"] not in pages or type(source["page"]) is not int
            or not 1 <= source["page"] <= pages[source["filename"]]
            for source in sources
        ):
            raise InputError(f"题集来源无效（{case_id}）")
        expected = tuple((source["filename"], source["page"]) for source in sources)
        groups = rules.get(case_id, ())
        reference = row["expected_answer"]
        if (len(set(expected)) != len(expected) or bool(expected) != bool(groups)
                or (reference == NO_RELEVANT_KNOWLEDGE) == bool(groups)):
            raise InputError(f"题集来源或拒答契约无效（{case_id}）")
        missing = [group.id for group in groups if not group.matches(_normalized(reference))]
        if missing:
            raise InputError(f"评分规则未覆盖人工参考答案（{case_id}，{', '.join(missing)}）")
        cases.append(EvalCase(case_id, row["category"], row["difficulty"], row["question"],
                              reference, expected, groups))
    return tuple(cases)


def load_inputs(eval_dir: Path) -> EvalInputs:
    """Verify the exact Day 17 inputs and compile every Day 18 fact group."""
    try:
        data = _text_bytes(eval_dir / "eval_dataset.jsonl")
        rubric = _text_bytes(eval_dir / "answer_rubric.json")
        corpus = _load_corpus(eval_dir, _text_bytes(eval_dir / "corpus_manifest.json"))
        return EvalInputs(_load_cases(data, rubric, corpus), corpus, sha256(rubric).hexdigest())
    except InputError:
        raise
    except (OSError, ValueError, TypeError, KeyError, re.error) as exc:
        raise InputError("无法读取或解析 Day18 输入文件") from exc


def score_observation(case: EvalCase, observation: Observation) -> EvalResult:
    """Keep execution errors unknown and require every page of multi-evidence cases."""
    answer = observation.answer
    expected = set(case.expected_sources)
    tool = observation.selected_tool
    mismatch = None if tool is None else tool != SEARCH_TOOL
    candidate_coverage = source_coverage = None
    answer_pass = False
    missing = None
    refused = None
    if answer is not None:
        refused = answer.answer == NO_RELEVANT_KNOWLEDGE
        if expected:
            candidates = {(item.filename, item.page) for item in observation.retrieved_chunks or ()}
            sources = {(item.filename, item.page) for item in answer.sources}
            candidate_coverage = len(expected & candidates) / len(expected)
            source_coverage = len(expected & sources) / len(expected)
            normalized = _normalized(answer.answer)
            missing = tuple(group.id for group in case.fact_groups if not group.matches(normalized))
            answer_pass = mismatch is False and not refused and not missing
        else:
            missing = ()
            answer_pass = mismatch is False and refused and not answer.sources
    return EvalResult(
        id=case.id, category=case.category, difficulty=case.difficulty,
        status="ok" if answer is not None else "error", error_code=observation.error_code,
        selected_tool=tool, tool_mismatch=mismatch, answer=answer.answer if answer is not None else None,
        sources=answer.sources if answer is not None else None, retrieved_chunks=observation.retrieved_chunks,
        candidate_source_hit=None if candidate_coverage is None else candidate_coverage == 1,
        source_hit=None if source_coverage is None else source_coverage == 1,
        candidate_source_coverage=candidate_coverage, source_coverage=source_coverage,
        answer_pass=answer_pass, missing_fact_groups=missing, refused=refused,
        latency_ms=observation.latency_ms, stop_run=observation.stop_run,
    )
