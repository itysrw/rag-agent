"""Offline contracts for the frozen Day 17 corpus and hand-labeled questions."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re
import unicodedata

from pypdf import PdfReader
import pytest


ROOT = Path(__file__).resolve().parents[2] / "eval"
FIELDS = {"id", "category", "question", "expected_answer", "expected_source", "difficulty"}
DISTRIBUTION = {
    "simple_fact": {"easy": 12, "medium": 6, "hard": 0},
    "cross_paragraph": {"easy": 2, "medium": 7, "hard": 3},
    "multi_hop": {"easy": 0, "medium": 4, "hard": 6},
    "unanswerable": {"easy": 1, "medium": 3, "hard": 6},
}
REFUSAL = "知识库中没有相关信息"


@pytest.fixture(autouse=True)
def isolated_conversation_dependency() -> None:
    """Keep this static module independent of the application fixture."""


@pytest.fixture(scope="module")
def cases() -> list[dict[str, object]]:
    data = (ROOT / "eval_dataset.jsonl").read_bytes()
    assert not data.startswith(b"\xef\xbb\xbf")
    assert data.endswith(b"\n")
    lines = data.decode("utf-8").splitlines()
    assert len(lines) == 50 and all(lines)
    return [json.loads(line) for line in lines]


@pytest.fixture(scope="module")
def manifest() -> dict[str, object]:
    return json.loads((ROOT / "corpus_manifest.json").read_text(encoding="utf-8"))


def test_dataset_has_exactly_fifty_distinct_self_contained_questions(
    cases: list[dict[str, object]],
) -> None:
    assert [case["id"] for case in cases] == [f"qa_{number:03d}" for number in range(1, 51)]
    questions = [case["question"] for case in cases]
    assert all(isinstance(question, str) and question.strip() for question in questions)
    normalized = [unicodedata.normalize("NFKC", question).casefold().strip() for question in questions]
    assert len(set(normalized)) == 50
    assert not any(re.search(r"上一题|刚才|上文|前一问", question) for question in questions)


def test_dataset_schema_and_distribution(cases: list[dict[str, object]]) -> None:
    assert all(set(case) == FIELDS for case in cases)
    actual = Counter((case["category"], case["difficulty"]) for case in cases)
    expected = Counter({
        (category, difficulty): count
        for category, by_difficulty in DISTRIBUTION.items()
        for difficulty, count in by_difficulty.items()
    })
    assert actual == expected
    assert all(isinstance(case["expected_answer"], str) and case["expected_answer"].strip() for case in cases)


def test_corpus_files_are_frozen_pdfs_with_valid_page_counts(
    manifest: dict[str, object],
) -> None:
    assert manifest["version"] == "day17-v1"
    assert manifest["source_policy_url"] == "https://www.ready.gov/publications"
    documents = manifest["documents"]
    assert len(documents) == 6
    assert len({document["filename"] for document in documents}) == len(documents)
    for document in documents:
        filename = document["filename"]
        assert re.fullmatch(r"[a-z-]+\.pdf", filename)
        path = ROOT / "corpus" / filename
        data = path.read_bytes()
        assert data.startswith(b"%PDF-")
        assert sha256(data).hexdigest() == document["sha256"]
        assert document["media_type"] == "application/pdf"
        assert document["page_count"] == len(PdfReader(path).pages) == 2
        assert document["source_url"].startswith("https://www.ready.gov/sites/default/files/")


def test_sources_and_refusals_match_frozen_corpus(
    cases: list[dict[str, object]], manifest: dict[str, object],
) -> None:
    pages = {document["filename"]: document["page_count"] for document in manifest["documents"]}
    cross_document = 0
    document_coverage: Counter[str] = Counter()
    for case in cases:
        sources = case["expected_source"]
        assert isinstance(sources, list)
        positions = set()
        for source in sources:
            assert set(source) == {"filename", "page"}
            assert source["filename"] in pages
            assert type(source["page"]) is int and 1 <= source["page"] <= pages[source["filename"]]
            position = (source["filename"], source["page"])
            assert position not in positions
            positions.add(position)
        category = case["category"]
        if category == "unanswerable":
            assert sources == [] and case["expected_answer"] == REFUSAL
        else:
            document_coverage.update({source["filename"] for source in sources})
            assert case["expected_answer"] != REFUSAL
            if category == "simple_fact":
                assert len(positions) == 1
            else:
                assert len(positions) >= 2
            if category == "multi_hop" and len({source["filename"] for source in sources}) >= 2:
                cross_document += 1
    assert cross_document >= 6
    assert len(document_coverage) == len(pages)
    assert all(count >= 3 for count in document_coverage.values())
    assert max(document_coverage.values()) < 20


def test_questions_and_answers_contain_no_internal_identifiers(
    cases: list[dict[str, object]],
) -> None:
    identity = re.compile(
        r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"
    )
    for case in cases:
        content = case["question"] + case["expected_answer"]
        assert not identity.search(content)
        assert not re.search(r"(?i)(?:[a-z]:\\|/home/|/users/|api[_-]?key|chunk[_-]?id|doc[_-]?id)", content)


@pytest.mark.parametrize(
    ("question", "filename", "evidence"),
    [
        pytest.param(
            "地震指南规定震后乘电梯到楼顶避险；应该先按哪一层？",
            "earthquake.pdf",
            "Do not use elevators.",
            id="earthquake-elevator",
        ),
        pytest.param(
            "洪水指南允许开车绕过路障的具体条件是什么？",
            "flood.pdf",
            "Never drive around barricades.",
            id="flood-barricades",
        ),
        pytest.param(
            "冬季风暴指南允许用燃气灶给房间取暖时，人与炉灶至少应保持几米？",
            "winter-storm.pdf",
            "Never heat your home with a gas stovetop or oven.",
            id="winter-storm-gas-stove",
        ),
    ],
)
def test_false_premise_with_explicit_corpus_rebuttal_is_not_unanswerable(
    cases: list[dict[str, object]], question: str, filename: str, evidence: str,
) -> None:
    """Reviewed false-premise questions need a grounded correction or replacement."""
    source = {"filename": filename, "page": 2}
    page_text = PdfReader(ROOT / "corpus" / filename).pages[1].extract_text()
    assert evidence in " ".join(page_text.split())

    matching_cases = [case for case in cases if case["question"] == question]
    if not matching_cases:
        return  # Replacing the flawed question is also a valid dataset correction.

    case = matching_cases[0]
    assert case["category"] != "unanswerable", f"{case['id']} ignores {source}"
    assert case["expected_answer"] != REFUSAL
    assert source in case["expected_source"]
