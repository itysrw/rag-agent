"""Verify that the demo transport uses the production upload format contract."""

import pytest
from fastapi.testclient import TestClient

from frontend import demo_backend


@pytest.mark.parametrize(
    ("name", "content", "mime", "status"),
    [
        ("guide.pdf", b"%PDF-1.7", "application/pdf", 201),
        ("notes.MD", b"# Demo", "text/markdown", 201),
        ("notes.md", b"# Demo", "text/plain", 201),
        ("notes.txt", b"demo", "text/plain", 201),
        ("notes.markdown", b"# Demo", "text/markdown", 415),
        ("notes.txt", b"demo", "application/octet-stream", 415),
        ("empty.txt", b"", "text/plain", 400),
    ],
)
def test_demo_upload_format(
    monkeypatch: pytest.MonkeyPatch, name: str, content: bytes, mime: str, status: int,
) -> None:
    monkeypatch.setattr(demo_backend, "_documents", [])
    with TestClient(demo_backend.app) as client:
        response = client.post("/documents/upload", files={"file": (name, content, mime)})
        catalog = client.get("/documents").json()["documents"]

    assert response.status_code == status
    if status == 201:
        assert catalog == [response.json()]
        assert catalog[0]["filename"] == name
    else:
        assert catalog == []
