"""Tests for complete and streamed chat responses."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from backend.app.api import chat as chat_module
from backend.app.api.chat import require_llm_client
from backend.app.main import app
from backend.app.services.llm import LLMConfigurationError, LLMServiceError


class StubLLMClient:
    """Deterministic replacement for the external model API."""

    model = "test-model"

    def complete(self, message: str) -> str:
        """Return a predictable complete response."""
        return f"reply:{message}"

    def stream(self, message: str) -> Iterator[str]:
        """Return predictable streamed deltas."""
        yield "reply:"
        yield message


class FailingLLMClient:
    """Stub that exposes the two upstream failure phases."""

    model = "test-model"

    def complete(self, message: str) -> str:
        """Fail before a non-streaming response starts."""
        del message
        raise LLMServiceError("complete failed")

    def stream(self, message: str) -> Iterator[str]:
        """Fail after the streaming response has emitted one event."""
        del message
        yield "partial"
        raise LLMServiceError("stream failed")


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Provide an API client with external LLM calls replaced."""
    app.dependency_overrides[require_llm_client] = StubLLMClient
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def test_chat_returns_complete_response(client: TestClient) -> None:
    """Non-streaming chat must trim input and return the active model."""
    response = client.post("/chat", json={"message": "  hello  "})

    assert response.status_code == 200
    assert response.json() == {
        "answer": "reply:hello",
        "model": "test-model",
    }


def test_chat_returns_sse_stream(client: TestClient) -> None:
    """Streaming chat must delimit every event and finish with DONE."""
    with client.stream(
        "POST",
        "/chat",
        json={"message": "hello", "stream": True},
    ) as response:
        body = response.read().decode("utf-8")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert body.split("\n\n") == [
        'data: {"delta": "reply:"}',
        'data: {"delta": "hello"}',
        "data: [DONE]",
        "",
    ]


def test_chat_rejects_blank_message(client: TestClient) -> None:
    """Whitespace-only user messages must fail validation."""
    response = client.post("/chat", json={"message": "   "})

    assert response.status_code == 422


def test_chat_returns_503_without_llm_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing API key must fail safely before entering the route."""

    def missing_client() -> StubLLMClient:
        raise LLMConfigurationError("missing key")

    app.dependency_overrides.clear()
    monkeypatch.setattr(chat_module, "get_llm_client", missing_client)

    with TestClient(app) as test_client:
        response = test_client.post("/chat", json={"message": "hello"})

    assert response.status_code == 503
    assert response.json() == {"detail": "The language model is not configured."}


def test_chat_maps_complete_failure_to_502() -> None:
    """A pre-response upstream failure must become HTTP 502."""
    app.dependency_overrides[require_llm_client] = FailingLLMClient
    try:
        with TestClient(app) as test_client:
            response = test_client.post("/chat", json={"message": "hello"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json() == {"detail": "The language model request failed."}


def test_chat_sends_error_event_after_stream_starts() -> None:
    """A started stream must report failure in-band instead of changing status."""
    app.dependency_overrides[require_llm_client] = FailingLLMClient
    try:
        with TestClient(app) as test_client:
            with test_client.stream(
                "POST",
                "/chat",
                json={"message": "hello", "stream": True},
            ) as response:
                body = response.read().decode("utf-8")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert body.split("\n\n") == [
        'data: {"delta": "partial"}',
        'event: error\ndata: {"detail": "The language model stream failed."}',
        "",
    ]
    assert "[DONE]" not in body
