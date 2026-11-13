"""Bounded, opt-in Day 19 full-RAG experiment helpers."""

import pytest

from backend.app.services.document_parser import PageText
from eval.agent import EvalStop
from eval.day19_full_comparison import BoundedBudget, split_bge_pages


class CharacterTokenizer:
    def encode(
        self, text: str, *, add_special_tokens: bool, truncation: bool,
    ) -> list[int]:
        assert add_special_tokens and not truncation
        return [0, *(ord(character) for character in text), 1]


def test_paid_request_budget_stops_before_excess_request() -> None:
    budget = BoundedBudget(2)
    budget.consume()
    budget.consume()
    with pytest.raises(EvalStop, match="budget_exhausted"):
        budget.consume()
    assert budget.attempts == 2
    with pytest.raises(ValueError):
        BoundedBudget(241)


def test_bge_variant_preserves_page_order_and_bounds_every_chunk() -> None:
    tokenizer = CharacterTokenizer()
    pages = [PageText(page=1, text="alpha " * 180), PageText(page=2, text="beta " * 130)]
    chunks = split_bge_pages(pages, tokenizer)
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    assert [chunk.page for chunk in chunks] == sorted(chunk.page for chunk in chunks)
    assert {chunk.page for chunk in chunks} == {1, 2}
    assert all(chunk.metadata["encoding_name"] == "bge-small-zh-v1.5" for chunk in chunks)
    assert all(len(tokenizer.encode(chunk.content, add_special_tokens=True, truncation=False)) <= 500
               for chunk in chunks)
