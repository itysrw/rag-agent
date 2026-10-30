"""Day 12 startup must not depend on a valid model configuration or snapshot."""

import pytest
import warnings
from fastapi.testclient import TestClient

from backend.app.api import rerank as rerank_api
from backend.app.core.config import RerankerSettings
from backend.app.main import create_app


def test_invalid_reranker_settings_fail_on_search_but_not_health(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[bool] = []
    def invalid_configuration() -> None:
        calls.append(True)
        RerankerSettings(_env_file=None, model_revision="invalid-private-setting")
    monkeypatch.setattr(rerank_api, "get_reranked_retrieval_service", invalid_configuration)
    application = create_app()
    with TestClient(application) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert calls == []
        response = client.post("/retrieval/rerank/search", json={"query": "question"})
    assert response.status_code == 503
    assert "invalid-private-setting" not in response.text
    assert calls == [True]


def test_routes_do_not_register_duplicate_operations() -> None:
    with warnings.catch_warnings(record=True) as recorded:
        create_app().openapi()
    assert not any("Duplicate Operation ID" in str(item.message) for item in recorded)


def test_health_does_not_construct_or_compile_graph(monkeypatch: pytest.MonkeyPatch) -> None:
    from typing import Any
    def forbidden(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("health must not construct graph dependencies")
    monkeypatch.setattr("backend.app.agent.graph.build_rag_graph", forbidden)
    monkeypatch.setattr("backend.app.services.rag.get_reranked_retrieval_service", forbidden)
    monkeypatch.setattr("backend.app.services.rag.get_llm_client", forbidden)
    with TestClient(create_app()) as client:
        assert client.get("/health").json() == {"status": "ok"}
