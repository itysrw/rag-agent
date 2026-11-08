"""Day 18 offline trial and explicitly authorized real evaluation entry point."""

import argparse
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from math import ceil
from pathlib import Path
import platform
from statistics import median
from typing import TextIO
from uuid import uuid4

from eval.agent import EvalAgent, EvalStop, MAX_LLM_REQUESTS, MockResponse, RequestBudget, build_mock_agent
from eval.scoring import (
    CATEGORY_COUNTS, CORPUS_VERSION, DATASET_SHA256, DATASET_VERSION, MANIFEST_SHA256,
    RUBRIC_VERSION, EvalCase, EvalInputs, EvalResult, InputError, load_inputs, score_observation,
)

EVAL_DIR = Path(__file__).resolve().parent
OUTPUT_ROOT = EVAL_DIR.parent / "data" / "eval" / "day18"
FORMAL_REPORT = EVAL_DIR / "eval_report.md"


@dataclass(frozen=True, slots=True)
class Rate:
    numerator: int
    denominator: int

    def render(self) -> str:
        """Show the counts even when a percentage cannot be computed."""
        if not self.denominator:
            return "0/0（无样本）"
        return f"{self.numerator}/{self.denominator}（{self.numerator / self.denominator:.1%}）"


@dataclass(frozen=True, slots=True)
class CategorySummary:
    accuracy: Rate
    coverage: Rate
    source_hit: Rate


@dataclass(frozen=True, slots=True)
class EvalSummary:
    attempted: int
    execution_errors: int
    not_run: int
    quality_failures: int
    accuracy: Rate
    coverage: Rate
    candidate_hit: Rate
    source_hit: Rate
    joint_pass: Rate
    correct_refusal: Rate
    refusal_rate: Rate
    unexpected_refusal: Rate
    categories: dict[str, CategorySummary]
    first_ms: float | None
    warm_count: int
    warm_p50_ms: float | None
    warm_p95_ms: float | None
    examples: dict[str, str]


def _failure_examples(results: Sequence[EvalResult]) -> dict[str, str]:
    examples = {}
    for item in results:
        if item.error_code:
            examples.setdefault("执行失败", f"{item.id}（{item.error_code}）")
            continue
        if item.tool_mismatch:
            examples.setdefault("工具误选", f"{item.id}（{item.selected_tool}）")
            continue
        if item.candidate_source_hit is False:
            examples.setdefault("候选缺页", item.id)
        if item.candidate_source_hit and item.source_hit is False:
            examples.setdefault("证据门排除必需页", item.id)
        if item.refused and item.source_hit is not None:
            examples.setdefault("有答案题拒答", item.id)
        if item.missing_fact_groups and not item.refused:
            missing = "、".join(item.missing_fact_groups)
            examples.setdefault("答案漏点或与规则冲突", f"{item.id}（{missing}）")
        if item.category == "unanswerable" and not item.answer_pass:
            examples.setdefault("未按契约拒答", item.id)
    return examples


def summarize(results: Sequence[EvalResult], expected_cases: Sequence[EvalCase]) -> EvalSummary:
    """Aggregate against the input population, including failed and unrun cases."""
    expected = {case.id: case for case in expected_cases}
    if len(expected) != len(expected_cases):
        raise ValueError("Expected case IDs must be unique.")
    ids = {result.id for result in results}
    if len(ids) != len(results) or not ids <= expected.keys():
        raise ValueError("Result IDs must be unique and belong to the input cases.")
    answerable = {case.id for case in expected_cases if case.expected_sources}
    successful = [result for result in results if result.status == "ok"]
    cited = [result for result in successful if result.id in answerable]
    categories = {}
    for category in CATEGORY_COUNTS:
        group_ids = {case.id for case in expected_cases if case.category == category}
        group = [result for result in successful if result.id in group_ids]
        categories[category] = CategorySummary(
            Rate(sum(result.answer_pass for result in group), len(group_ids)),
            Rate(len(group), len(group_ids)),
            Rate(sum(result.source_hit is True for result in group), len(group_ids & answerable)),
        )
    warm = sorted(result.latency_ms for result in results[1:])
    joint = sum(result.answer_pass and result.source_hit is True for result in cited)
    refusals = sum(result.answer_pass for result in successful if result.id not in answerable)
    return EvalSummary(
        attempted=len(results), execution_errors=len(results) - len(successful),
        not_run=len(expected) - len(results), quality_failures=len(successful) - joint - refusals,
        accuracy=Rate(sum(result.answer_pass for result in successful), len(expected)),
        coverage=Rate(len(successful), len(expected)),
        candidate_hit=Rate(sum(result.candidate_source_hit is True for result in cited), len(answerable)),
        source_hit=Rate(sum(result.source_hit is True for result in cited), len(answerable)),
        joint_pass=Rate(joint, len(answerable)),
        correct_refusal=Rate(refusals, len(expected) - len(answerable)),
        refusal_rate=Rate(sum(result.refused is True for result in successful), len(successful)),
        unexpected_refusal=Rate(sum(result.refused is True for result in cited), len(answerable)),
        categories=categories, first_ms=results[0].latency_ms if results else None,
        warm_count=len(warm), warm_p50_ms=median(warm) if warm else None,
        warm_p95_ms=warm[ceil(0.95 * len(warm)) - 1] if warm else None,
        examples=_failure_examples(results),
    )


@dataclass(slots=True)
class RunMetadata:
    run_id: str
    mode: str
    started_at: str
    rubric_sha256: str
    max_llm_requests: int | None
    status: str = "running"
    stop_reason: str | None = None
    finished_at: str | None = None
    llm_attempts: int = 0
    runtime: dict[str, object] | None = None
    dataset_version: str = DATASET_VERSION
    dataset_sha256: str = DATASET_SHA256
    corpus_version: str = CORPUS_VERSION
    corpus_manifest_sha256: str = MANIFEST_SHA256
    rubric_version: str = RUBRIC_VERSION
    python: str = platform.python_version()


def _ms(value: float | None) -> str:
    return "无样本" if value is None else f"{value:.2f} ms"


def render_report(summary: EvalSummary, metadata: RunMetadata) -> str:
    """Render metrics with the population, success coverage and timing boundary."""
    is_mock = metadata.mode == "mock"
    heading = "模拟诊断" if is_mock else ("正式基线" if metadata.status == "complete" else "不完整诊断")
    run_info = metadata.runtime or {}
    model = run_info.get("model", "未初始化")
    lines = [
        f"# Day18 RAG 评测 · {heading}", "",
        f"运行 {metadata.run_id}，模式 {metadata.mode}，状态 {metadata.status}。",
        f"冻结题集 {metadata.dataset_version}，英文语料 {metadata.corpus_version}，"
        f"中文单轮问答，规则 {metadata.rubric_version}，模型 {model}。", "",
        "测量从现有 LangGraph 单轮执行开始到返回或失败，覆盖工具选择、检索、重排和生成。"
        "HTTP、会话落库、评分和写报告的耗时独立于此计时。",
        "答案通过要求走知识检索并覆盖全部事实组。引用通过要求全部必需的文件名和物理页码匹配。"
        "执行失败和未运行题都保留在预定分母中。", "",
    ]
    if is_mock:
        lines.extend(["**以下是用固定替身构造的模拟结果，仅用于核验执行和统计。**", ""])
    if metadata.stop_reason:
        lines.extend([f"停止原因为 {metadata.stop_reason}。", ""])
    lines.extend([
        f"尝试 **{summary.attempted}** 题，执行失败 **{summary.execution_errors}** 题，"
        f"未运行 **{summary.not_run}** 题。正常返回中有 **{summary.quality_failures}** 题"
        "未通过答案与引用的联合要求或拒答要求。", "",
        "| 指标 | 结果 |", "|---|---:|",
        f"| 整体规则准确率 | {summary.accuracy.render()} |",
        f"| 正常返回覆盖率 | {summary.coverage.render()} |",
        f"| 候选来源全命中率（有答案题） | {summary.candidate_hit.render()} |",
        f"| 最终引用全命中率（有答案题） | {summary.source_hit.render()} |",
        f"| 答案与引用联合通过率（有答案题） | {summary.joint_pass.render()} |",
        f"| 正确拒答率（无答案题） | {summary.correct_refusal.render()} |",
        f"| 正常返回中的固定拒答率 | {summary.refusal_rate.render()} |",
        f"| 有答案题固定拒答率 | {summary.unexpected_refusal.render()} |", "",
        "| 题类 | 规则通过 | 正常返回 | 最终引用全命中 |", "|---|---:|---:|---:|",
    ])
    for category, group in summary.categories.items():
        source = group.source_hit.render() if group.source_hit.denominator else "不适用"
        lines.append(f"| {category} | {group.accuracy.render()} | {group.coverage.render()} | {source} |")
    lines.extend([
        "", "## 延迟", "",
        f"- 首题（独立列出，包含首次模型加载，如有）为 {_ms(summary.first_ms)}。",
        f"- 后续 {summary.warm_count} 次尝试的 P50 为 {_ms(summary.warm_p50_ms)}，"
        f"P95 为 {_ms(summary.warm_p95_ms)}。P50 取中位数，P95 取向上取整的排序名次。", "",
        "## 典型失败", "",
    ])
    lines.extend([f"- {label}见 {value}。" for label, value in summary.examples.items()]
                 or ["逐题记录中没有上述失败样本。"])
    lines.extend([
        "", "## 复算记录", "",
        f"- 题集 SHA-256 为 {metadata.dataset_sha256}。",
        f"- 语料清单 SHA-256 为 {metadata.corpus_manifest_sha256}。",
        f"- 评分规则 SHA-256 为 {metadata.rubric_sha256}。",
        f"- LLM 请求实际尝试 {metadata.llm_attempts} 次"
        + (f"，预算 {metadata.max_llm_requests} 次。" if metadata.max_llm_requests is not None else "。"),
        f"- 本地运行目录为 data/eval/day18/{metadata.run_id}/，其中保存逐题 JSONL 和运行清单。",
        "- 关键词规则提供近似判分，逐题样本可人工复核。", "",
    ])
    return "\n".join(lines)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _write_atomic(path: Path, content: str) -> None:
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _mock_agent(cases: Sequence[EvalCase]) -> EvalAgent:
    responses = {}
    for case in cases:
        score = 0.1 if case.id == "qa_001" else 0.9
        # Fixed probes exercise the evidence gate, a missing fact and partial citation coverage.
        sources = case.expected_sources[:-1] if case.id == "qa_032" else case.expected_sources
        answer = "可能引发海啸。" if case.id == "qa_020" else case.expected_answer
        responses[case.question] = MockResponse(answer, tuple((file, page, score) for file, page in sources))
    return build_mock_agent(responses)


def _run_cases(
    cases: Sequence[EvalCase], agent: EvalAgent, stream: TextIO, results: list[EvalResult],
    budget: RequestBudget | None,
) -> str | None:
    for case in cases:
        if budget is not None and budget.attempts >= budget.limit:
            return "budget_exhausted"
        result = score_observation(case, agent.run(case.question))
        stream.write(json.dumps(asdict(result), ensure_ascii=False, allow_nan=False) + "\n")
        stream.flush()
        results.append(result)
        if result.stop_run:
            return result.error_code
    return None


@dataclass(frozen=True, slots=True)
class RunOutcome:
    directory: Path
    metadata: RunMetadata
    summary: EvalSummary


def run_evaluation(
    inputs: EvalInputs,
    *,
    mode: str,
    allow_paid: bool = False,
    max_llm_requests: int | None = None,
    output_root: Path = OUTPUT_ROOT,
    formal_report: Path = FORMAL_REPORT,
) -> RunOutcome:
    """Persist each attempted question and publish only a complete real report."""
    budget = None
    if mode == "real" and allow_paid and max_llm_requests is not None:
        budget = RequestBudget(max_llm_requests)
    elif mode != "mock" or allow_paid or max_llm_requests is not None:
        raise ValueError("真实模式需要显式付费开关和预算，模拟模式不接受付费选项")

    started = datetime.now(timezone.utc)
    run_id = f"{started:%Y%m%dT%H%M%SZ}-{mode}-{uuid4().hex[:12]}"
    directory = output_root / run_id
    directory.mkdir(parents=True, exist_ok=False)
    metadata = RunMetadata(run_id, mode, started.isoformat(timespec="seconds"),
                           inputs.rubric_sha256, max_llm_requests)
    manifest_path = directory / "run_metadata.json"
    _write_atomic(manifest_path, json.dumps(asdict(metadata), ensure_ascii=False, indent=2) + "\n")
    results: list[EvalResult] = []

    with (directory / "eval_results.jsonl").open("x", encoding="utf-8", newline="\n") as stream:
        try:
            if budget is None:
                agent = _mock_agent(inputs.cases)
                metadata.runtime = {"model": agent.model, "synthetic": True}
                metadata.stop_reason = _run_cases(inputs.cases, agent, stream, results, budget)
            else:
                from eval.real import open_real_run

                with open_real_run(inputs.corpus, budget) as real:
                    metadata.runtime = real.details
                    metadata.stop_reason = _run_cases(inputs.cases, real.agent, stream, results, budget)
                    if metadata.stop_reason is None and all(item.status == "ok" for item in results):
                        real.verify_final_corpus()
        except EvalStop as exc:
            metadata.stop_reason = exc.code
        except KeyboardInterrupt:
            metadata.stop_reason = "interrupted"
        except Exception:
            if budget is None:
                raise
            metadata.stop_reason = "real_run_failed"

    summary = summarize(results, inputs.cases)
    if summary.execution_errors and metadata.stop_reason is None:
        metadata.stop_reason = "execution_errors"
    metadata.status = "complete" if not (summary.not_run or metadata.stop_reason) else "incomplete"
    metadata.llm_attempts = 0 if budget is None else budget.attempts
    metadata.finished_at = _utc_now()
    report = render_report(summary, metadata)
    _write_atomic(directory / "eval_report.md", report)
    _write_atomic(manifest_path, json.dumps({**asdict(metadata), "summary": asdict(summary)},
                                            ensure_ascii=False, indent=2) + "\n")
    if mode == "real" and metadata.status == "complete":
        _write_atomic(formal_report, report)
    return RunOutcome(directory, metadata, summary)


def main(argv: Sequence[str] | None = None) -> int:
    """Validate the CLI before reading configuration or initializing a run."""
    parser = argparse.ArgumentParser(description="Day18 RAG 单轮评测")
    parser.add_argument("--mode", choices=("mock", "real"), required=True)
    parser.add_argument("--allow-paid", action="store_true")
    parser.add_argument("--max-llm-requests", type=int)
    args = parser.parse_args(argv)
    if args.mode == "real" and (
        not args.allow_paid or args.max_llm_requests is None
        or not 1 <= args.max_llm_requests <= MAX_LLM_REQUESTS
    ):
        parser.error("real 模式要求 --allow-paid 和 1 至 100 的 --max-llm-requests")
    if args.mode == "mock" and (args.allow_paid or args.max_llm_requests is not None):
        parser.error("mock 模式不接受付费选项")
    try:
        inputs = load_inputs(EVAL_DIR)
    except InputError as exc:
        parser.error(str(exc))
    outcome = run_evaluation(inputs, mode=args.mode, allow_paid=args.allow_paid,
                             max_llm_requests=args.max_llm_requests)
    print(outcome.directory)
    return 0 if outcome.metadata.status == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
