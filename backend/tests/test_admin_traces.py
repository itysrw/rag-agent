"""Admin trace access boundaries, paging and stable ordering."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi.testclient import TestClient
import pytest

from backend.app.api import admin_traces
from backend.app.core.config import AdminTraceSettings, get_admin_trace_settings
from backend.app.main import app
from backend.app.services.request_trace import TraceRecorder, get_request_trace_store


def test_token_is_loaded_from_environment_and_redacted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_TRACE_TOKEN", "environment-secret")
    get_admin_trace_settings.cache_clear()
    try:
        settings = get_admin_trace_settings()
        assert settings.token is not None
        assert settings.token.get_secret_value() == "environment-secret"
        assert "environment-secret" not in repr(settings)
    finally:
        get_admin_trace_settings.cache_clear()


def test_missing_or_wrong_admin_token_never_queries_traces(monkeypatch: pytest.MonkeyPatch) -> None:
    class ForbiddenStore:
        def recent(self, limit: int) -> list[object]:
            raise AssertionError("unauthorized request reached trace storage")

    monkeypatch.setattr(admin_traces, "get_admin_trace_settings", lambda: AdminTraceSettings(_env_file=None, token="secret"))
    app.dependency_overrides[admin_traces.get_request_trace_store] = lambda: ForbiddenStore()
    try:
        with TestClient(app) as client:
            missing = client.get("/admin/traces")
            wrong = client.get("/admin/traces", headers={"X-Admin-Token": "wrong"})
    finally:
        app.dependency_overrides.clear()
    assert missing.status_code == wrong.status_code == 403
    assert missing.headers["Cache-Control"] == wrong.headers["Cache-Control"] == "no-store"
    assert "secret" not in missing.text + wrong.text

    monkeypatch.setattr(admin_traces, "get_admin_trace_settings", lambda: AdminTraceSettings(_env_file=None, token=None))
    with TestClient(app) as client:
        disabled = client.get("/admin/traces", headers={"X-Admin-Token": "secret"})
    assert disabled.status_code == 503 and disabled.headers["Cache-Control"] == "no-store"


def test_recent_traces_limit_order_empty_and_cache_control(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(admin_traces, "get_admin_trace_settings", lambda: AdminTraceSettings(_env_file=None, token="secret"))
    headers = {"X-Admin-Token": "secret"}
    with TestClient(app) as client:
        empty = client.get("/admin/traces", headers=headers)
    assert empty.status_code == 200 and empty.json() == []

    store = get_request_trace_store()
    timestamp = datetime.now(timezone.utc) - timedelta(days=1)
    first = TraceRecorder("first", mode="json")
    first.id = UUID("00000000-0000-0000-0000-000000000001")
    first.created_at = timestamp
    first.finish(store, outcome="success", http_status=200)
    second = TraceRecorder("second", mode="json")
    second.id = UUID("00000000-0000-0000-0000-000000000002")
    second.created_at = timestamp
    second.finish(store, outcome="error", http_status=502, error_code="LLMServiceError")
    newest = TraceRecorder("newest", mode="sse")
    newest.finish(store, outcome="cancelled", http_status=200)

    with TestClient(app) as client:
        one = client.get("/admin/traces?limit=1", headers=headers)
        all_rows = client.get("/admin/traces?limit=100", headers=headers)
        zero = client.get("/admin/traces?limit=0", headers=headers)
        too_many = client.get("/admin/traces?limit=101", headers=headers)
    assert one.status_code == all_rows.status_code == 200
    assert [item["id"] for item in one.json()] == [str(newest.id)]
    assert [item["id"] for item in all_rows.json()] == [str(newest.id), str(second.id), str(first.id)]
    assert all_rows.json()[0]["query"] == "newest"
    assert all_rows.json()[0]["business_committed"] is False
    assert zero.status_code == too_many.status_code == 422
    for response in (empty, one, all_rows, zero, too_many):
        assert response.headers["Cache-Control"] == "no-store"
    assert "secret" not in all_rows.text


def test_admin_store_failure_is_safe_and_not_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    class BrokenStore:
        def recent(self, limit: int) -> list[object]:
            raise RuntimeError("private database address")

    monkeypatch.setattr(admin_traces, "get_admin_trace_settings", lambda: AdminTraceSettings(_env_file=None, token="secret"))
    app.dependency_overrides[admin_traces.get_request_trace_store] = lambda: BrokenStore()
    try:
        with TestClient(app) as client:
            response = client.get("/admin/traces", headers={"X-Admin-Token": "secret"})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 503
    assert response.headers["Cache-Control"] == "no-store"
    assert "private database address" not in response.text
