"""Small dependency-free PDF fixtures for parser tests."""


def build_text_pdf(page_texts: list[str]) -> bytes:
    """Build a minimal PDF with one text stream per requested page."""
    if not page_texts:
        raise ValueError("At least one page is required")

    page_count = len(page_texts)
    font_id = 3 + page_count * 2
    descendant_font_id = font_id + 1
    page_ids = [3 + index * 2 for index in range(page_count)]
    content_ids = [page_id + 1 for page_id in page_ids]
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: (
            f"<< /Type /Pages /Kids [{' '.join(f'{page_id} 0 R' for page_id in page_ids)}] "
            f"/Count {page_count} >>"
        ).encode("ascii"),
        font_id: (
            f"<< /Type /Font /Subtype /Type0 /BaseFont /STSong-Light "
            f"/Encoding /UniGB-UCS2-H "
            f"/DescendantFonts [{descendant_font_id} 0 R] >>"
        ).encode("ascii"),
        descendant_font_id: (
            b"<< /Type /Font /Subtype /CIDFontType0 /BaseFont /STSong-Light "
            b"/CIDSystemInfo << /Registry (Adobe) /Ordering (GB1) "
            b"/Supplement 4 >> >>"
        ),
    }

    for page_id, content_id, text in zip(page_ids, content_ids, page_texts, strict=True):
        objects[page_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> "
            f"/Contents {content_id} 0 R >>"
        ).encode("ascii")
        stream = _build_text_stream(text)
        objects[content_id] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream
            + b"\nendstream"
        )

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for object_id in range(1, descendant_font_id + 1):
        offsets.append(len(output))
        output.extend(f"{object_id} 0 obj\n".encode("ascii"))
        output.extend(objects[object_id])
        output.extend(b"\nendobj\n")

    xref_offset = len(output)
    output.extend(f"xref\n0 {descendant_font_id + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        (
            f"trailer\n<< /Size {descendant_font_id + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(output)


def _build_text_stream(text: str) -> bytes:
    """Encode text as UCS-2-compatible UTF-16BE for the Type0 test font."""
    if not text:
        return b""
    encoded_hex = text.encode("utf-16-be").hex().upper()
    return f"BT /F1 12 Tf 72 720 Td <{encoded_hex}> Tj ET".encode("ascii")
