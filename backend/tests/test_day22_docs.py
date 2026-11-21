"""Regression checks for the published Day 22 deployment and metric contracts."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]


def test_quick_start_warns_to_stop_legacy_qdrant_before_reusing_index() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    _, heading, rest = readme.partition("## 快速启动\n")
    assert heading, "README must expose its quick-start instructions."
    quick_start = rest.split("\n## ", 1)[0]
    start = re.search(r"(?m)^\s*docker(?: compose|-compose)\s+up\b", quick_start)
    assert start is not None, "Quick start must show the default Compose startup command."

    before_start = quick_start[:start.start()]
    stop_old_qdrant = re.search(
        r"(?:停止|关闭|停掉|关停)[^\n。；]{0,50}(?:旧[^\n。；]{0,25}Qdrant|Qdrant[^\n。；]{0,25}旧)"
        r"|旧[^\n。；]{0,25}Qdrant[^\n。；]{0,50}(?:停止|关闭|停掉|关停)"
        r"|\bdocker\s+(?:container\s+)?stop\s+[^\n`]*qdrant",
        before_start,
        flags=re.IGNORECASE,
    )
    assert stop_old_qdrant, "Before default Compose startup, explain that reusing an old index requires stopping the old Qdrant instance."


def test_evaluation_summary_does_not_describe_overall_pass_as_joint_pass() -> None:
    summary = (ROOT / "docs" / "evaluation-summary.md").read_text(encoding="utf-8")
    row = re.search(r"(?m)^\|\s*整体规则通过(?:率)?\s*\|[^|\n]+\|([^|\n]+)\|", summary)
    assert row is not None, "The public summary must explain the overall rule pass metric."
    definition = row.group(1).strip()

    assert not re.match(r"(?:有答案题(?:的|[:：]\s*)?)?答案与引用联合通过", definition), definition
