"""Fixed Day 10 vector-versus-BM25 comparison cases."""

from __future__ import annotations

from typing import Literal, TypedDict


class Day10ComparisonCase(TypedDict):
    """One precommitted positive query and objective hit phrase."""

    category: Literal["exact_identifier", "semantic_paraphrase", "mixed"]
    question: str
    expected_phrase: str


COMPARISON_CASES: tuple[Day10ComparisonCase, ...] = (
    {
        "category": "exact_identifier",
        "question": "6203",
        "expected_phrase": "服务分机是 6203",
    },
    {
        "category": "exact_identifier",
        "question": "五万元采购",
        "expected_phrase": "总经理审批",
    },
    {
        "category": "exact_identifier",
        "question": "网络组",
        "expected_phrase": "服务分机是 6203",
    },
    {
        "category": "exact_identifier",
        "question": "全量备份",
        "expected_phrase": "每周日凌晨两点",
    },
    {
        "category": "semantic_paraphrase",
        "question": "远程接入工具坏了应该找谁处理？",
        "expected_phrase": "服务分机是 6203",
    },
    {
        "category": "semantic_paraphrase",
        "question": "新人多久能拿到办公设备？",
        "expected_phrase": "三个工作日内发放",
    },
    {
        "category": "semantic_paraphrase",
        "question": "差旅单据交财务的截止日是什么时候？",
        "expected_phrase": "每月二十五日前",
    },
    {
        "category": "semantic_paraphrase",
        "question": "周末什么时候做整库备份？",
        "expected_phrase": "每周日凌晨两点",
    },
    {
        "category": "mixed",
        "question": "VPN 出错后拨打哪个 6203 服务？",
        "expected_phrase": "服务分机是 6203",
    },
    {
        "category": "mixed",
        "question": "采购超过五万元要找最高负责人审批吗？",
        "expected_phrase": "总经理审批",
    },
    {
        "category": "mixed",
        "question": "访客登记后如何进入办公区？",
        "expected_phrase": "访客登记",
    },
    {
        "category": "mixed",
        "question": "会议室最多能占用多久？",
        "expected_phrase": "最长不得超过两个小时",
    },
)


NEGATIVE_QUESTIONS: tuple[str, ...] = (
    "python decorator syntax",
    "lunar crater geology",
    "weather forecast typhoon",
)
