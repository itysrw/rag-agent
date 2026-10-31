"""Opt-in real DeepSeek acceptance for question-driven Day15 tool selection."""

from __future__ import annotations

import os
from uuid import UUID

import pytest

from backend.app.agent.tools import TOOL_SELECTION_PROMPT, tool_definitions
from backend.app.core.config import LLMSettings
from backend.app.services.llm import AgentToolCall, LLMClient

DOC_ID = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("RUN_LLM_TOOL_SELECTION_INTEGRATION") != "1"
        or os.environ.get("LLM_API_KEY", "").strip() in {"", "your_api_key_here"},
        reason=(
            "set RUN_LLM_TOOL_SELECTION_INTEGRATION=1 and provide LLM_API_KEY "
            "in the process environment to call the real selector"
        ),
    ),
]


def test_real_deepseek_selects_one_correct_tool_for_each_question() -> None:
    """Exercise the production prompt and schemas without reading the project .env."""
    client = LLMClient(LLMSettings(
        _env_file=None,
        base_url="https://api.deepseek.com",
        model="deepseek-v4-flash",
    ))
    cases: tuple[tuple[str, AgentToolCall], ...] = (
        (
            "有哪些文档？",
            AgentToolCall(call_id="ignored", name="list_documents", arguments={}),
        ),
        (
            f"文档 {DOC_ID} 的详情是什么？",
            AgentToolCall(
                call_id="ignored",
                name="get_document_detail",
                arguments={"doc_id": str(DOC_ID)},
            ),
        ),
        (
            "报销流程是什么？",
            AgentToolCall(
                call_id="ignored",
                name="search_knowledge_base",
                arguments={"query": "报销流程是什么？"},
            ),
        ),
    )

    selected: list[tuple[str, dict[str, str]]] = []
    for question, expected in cases:
        call = client.select_tool(
            (
                {"role": "system", "content": TOOL_SELECTION_PROMPT},
                {"role": "user", "content": question},
            ),
            tool_definitions(),
        )
        selected.append((call["name"], call["arguments"]))
        assert call["name"] == expected["name"]
        assert call["arguments"] == expected["arguments"]

    assert len(selected) == 3
