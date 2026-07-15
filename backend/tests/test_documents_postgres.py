"""Opt-in local PostgreSQL integration test for the upload endpoint."""

import os
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import DocumentSettings, get_document_settings
from backend.app.core.database import get_session_factory
from backend.app.main import app
from backend.app.models.document import Document
from backend.app.services.document_storage import build_upload_paths
from backend.tests.pdf_fixtures import build_text_pdf

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    os.environ.get("RUN_POSTGRES_INTEGRATION") != "1",
    reason="set RUN_POSTGRES_INTEGRATION=1 for the local PostgreSQL test",
)
def test_upload_round_trip_with_local_postgres(tmp_path: Path) -> None:
    """Persist a real PDF through the endpoint and remove acceptance artifacts."""
    settings = DocumentSettings(
        _env_file=None,
        upload_dir=tmp_path / "uploads",
        max_upload_size=20 * 1024 * 1024,
        max_pdf_pages=500,
        read_chunk_size=1024 * 1024,
    )
    app.dependency_overrides[get_document_settings] = lambda: settings
    document_id: UUID | None = None
    pdf = build_text_pdf(["first", "", "third"])
    try:
        with TestClient(app) as client:
            response = client.post(
                "/documents/upload",
                files={"file": ("postgres-check.pdf", pdf, "application/pdf")},
            )

        assert response.status_code == 201
        document_id = UUID(response.json()["id"])
        with get_session_factory()() as session:
            document = session.get(Document, document_id)
            assert document is not None
            assert document.extracted_text.count("\f") == 2
            assert "first" in document.extracted_text
            assert "third" in document.extracted_text
            session.delete(document)
            session.commit()

        paths = build_upload_paths(settings.upload_dir, document_id, ".pdf")
        assert paths.final.read_bytes() == pdf
        paths.final.unlink()
    finally:
        app.dependency_overrides.clear()
        if document_id is not None:
            paths = build_upload_paths(settings.upload_dir, document_id, ".pdf")
            paths.part.unlink(missing_ok=True)
            paths.final.unlink(missing_ok=True)
