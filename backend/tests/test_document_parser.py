"""Tests for page-aware PDF, Markdown, and TXT extraction."""

from pathlib import Path

import pytest
from pypdf import PdfWriter

from backend.app.services.document_parser import (
    EncryptedPdfError,
    InvalidPdfError,
    InvalidTextEncodingError,
    NoExtractableTextError,
    PdfPageLimitError,
    PageText,
    parse_document,
    serialize_pages,
)
from backend.tests.pdf_fixtures import build_text_pdf


def parse(path: Path, extension: str, max_pdf_pages: int = 500) -> list[PageText]:
    """Parse with the fixed Day 4 text read chunk size."""
    return parse_document(
        path,
        extension,
        max_pdf_pages=max_pdf_pages,
        read_chunk_size=1024,
    )


def test_pdf_preserves_blank_page_boundaries(tmp_path: Path) -> None:
    """Blank PDF pages remain represented between form-feed delimiters."""
    path = tmp_path / "pages.pdf"
    path.write_bytes(build_text_pdf(["first", "", "third"]))

    pages = parse(path, ".pdf")

    assert [page.page for page in pages] == [1, 2, 3]
    assert "first" in pages[0].text
    assert pages[1].text == ""
    assert "third" in pages[2].text
    assert serialize_pages(pages).count("\f") == 2


def test_pdf_rejects_when_every_page_is_blank(tmp_path: Path) -> None:
    """A PDF with no text layer is not accepted as ready."""
    path = tmp_path / "blank.pdf"
    path.write_bytes(build_text_pdf(["", ""]))

    with pytest.raises(NoExtractableTextError):
        parse(path, ".pdf")


def test_pdf_rejects_page_count_over_limit(tmp_path: Path) -> None:
    """The page limit is checked before extracting every page."""
    path = tmp_path / "many.pdf"
    path.write_bytes(build_text_pdf(["one", "two"]))

    with pytest.raises(PdfPageLimitError):
        parse(path, ".pdf", max_pdf_pages=1)


def test_pdf_rejects_encrypted_input(tmp_path: Path) -> None:
    """Password-protected PDFs are outside Day 4 scope."""
    path = tmp_path / "encrypted.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.encrypt("secret")
    with path.open("wb") as destination:
        writer.write(destination)

    with pytest.raises(EncryptedPdfError):
        parse(path, ".pdf")


def test_pdf_rejects_damaged_input(tmp_path: Path) -> None:
    """Malformed PDF bytes become a safe parser error."""
    path = tmp_path / "damaged.pdf"
    path.write_bytes(b"%PDF-1.7\nnot-a-real-pdf")

    with pytest.raises(InvalidPdfError):
        parse(path, ".pdf")


def test_utf8_bom_is_removed_and_text_is_page_one(tmp_path: Path) -> None:
    """UTF-8 BOM input is accepted without retaining the marker."""
    path = tmp_path / "notes.md"
    path.write_bytes(b"\xef\xbb\xbfhello")

    pages = parse(path, ".md")

    assert len(pages) == 1
    assert pages[0].page == 1
    assert pages[0].text == "hello"


def test_non_utf8_text_is_rejected(tmp_path: Path) -> None:
    """Day 4 text documents require strict UTF-8 decoding."""
    path = tmp_path / "legacy.txt"
    path.write_bytes(b"\xff\xfeinvalid")

    with pytest.raises(InvalidTextEncodingError):
        parse(path, ".txt")
