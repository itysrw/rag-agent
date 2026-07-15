"""Text extraction that preserves source page boundaries."""

from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import FileNotDecryptedError, PdfReadError

PAGE_SEPARATOR = "\f"


@dataclass(frozen=True, slots=True)
class PageText:
    """Extracted text associated with one one-based source page."""

    page: int
    text: str


class DocumentParseError(ValueError):
    """Base class for safe client-facing parsing failures."""


class InvalidPdfError(DocumentParseError):
    """Raised when a PDF is structurally invalid or damaged."""


class EncryptedPdfError(DocumentParseError):
    """Raised when a PDF requires a password."""


class PdfPageLimitError(DocumentParseError):
    """Raised when a PDF exceeds the configured page limit."""


class InvalidTextEncodingError(DocumentParseError):
    """Raised when Markdown or TXT content is not UTF-8."""


class NoExtractableTextError(DocumentParseError):
    """Raised when every source page is empty or whitespace-only."""


def parse_document(
    path: Path,
    extension: str,
    *,
    max_pdf_pages: int,
    read_chunk_size: int,
) -> list[PageText]:
    """Extract pages from one supported document."""
    normalized_extension = extension.lower()
    if normalized_extension == ".pdf":
        pages = _parse_pdf(path, max_pdf_pages=max_pdf_pages)
    elif normalized_extension in {".md", ".txt"}:
        pages = [_parse_utf8_text(path, read_chunk_size=read_chunk_size)]
    else:
        raise DocumentParseError("Unsupported document extension")

    if not any(page.text.strip() for page in pages):
        raise NoExtractableTextError("The document contains no extractable text")
    return pages


def serialize_pages(pages: list[PageText]) -> str:
    """Join pages with the standard form-feed page delimiter."""
    return PAGE_SEPARATOR.join(page.text for page in pages)


def _parse_pdf(path: Path, *, max_pdf_pages: int) -> list[PageText]:
    try:
        reader = PdfReader(path, strict=False)
        if reader.is_encrypted:
            raise EncryptedPdfError("Encrypted PDF files are not supported")
        if len(reader.pages) > max_pdf_pages:
            raise PdfPageLimitError("The PDF exceeds the page limit")

        pages: list[PageText] = []
        for page_number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").replace(PAGE_SEPARATOR, "\n")
            pages.append(PageText(page=page_number, text=text))
        return pages
    except DocumentParseError:
        raise
    except MemoryError:
        raise
    except (FileNotDecryptedError, PdfReadError, EOFError, ValueError) as exc:
        raise InvalidPdfError("The PDF is invalid or damaged") from exc
    except Exception as exc:
        raise InvalidPdfError("The PDF is invalid or damaged") from exc


def _parse_utf8_text(path: Path, *, read_chunk_size: int) -> PageText:
    chunks: list[str] = []
    try:
        with path.open("r", encoding="utf-8-sig", errors="strict") as source:
            while chunk := source.read(read_chunk_size):
                chunks.append(chunk)
    except UnicodeDecodeError as exc:
        raise InvalidTextEncodingError("Text documents must use UTF-8") from exc

    text = "".join(chunks).replace(PAGE_SEPARATOR, "\n")
    return PageText(page=1, text=text)
