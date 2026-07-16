"""Tests for the provider-neutral OpenAI-compatible client."""

from types import SimpleNamespace
from typing import Any

import pytest
from openai import OpenAIError
from pydantic import SecretStr

from backend.app.core.config import LLMSettings
from backend.app.services.llm import LLMClient, LLMMessage, LLMServiceError


class FakeStream:
    """Closable iterator that can fail after its prepared chunks."""

    def __init__(
        self,
        chunks: list[Any],
        error: OpenAIError | None = None,
    ) -> None:
        self._chunks = iter(chunks)
        self._error = error
        self.closed = False

    def __iter__(self) -> "FakeStream":
        return self

    def __next__(self) -> Any:
        try:
            return next(self._chunks)
        except StopIteration:
            if self._error is not None:
                error = self._error
                self._error = None
                raise error
            raise

    def close(self) -> None:
        """Record that the client released the upstream response."""
        self.closed = True


class FakeCompletions:
    """Record compatible SDK calls and return deterministic responses."""

    def __init__(self, stream_error: OpenAIError | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self.stream_response = FakeStream(
            [
                SimpleNamespace(
                    choices=[SimpleNamespace(delta=SimpleNamespace(content="A"))]
                ),
                SimpleNamespace(
                    choices=[SimpleNamespace(delta=SimpleNamespace(content=None))]
                ),
                SimpleNamespace(
                    choices=[SimpleNamespace(delta=SimpleNamespace(content="B"))]
                ),
            ],
            error=stream_error,
        )

    def create(self, **kwargs: Any) -> Any:
        """Return either a complete response or streamed chunks."""
        self.calls.append(kwargs)
        if kwargs["stream"]:
            return self.stream_response
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="complete"))]
        )


class FakeSDKClient:
    """Expose the minimal nested chat completion SDK surface."""

    def __init__(self, stream_error: OpenAIError | None = None) -> None:
        self.completions = FakeCompletions(stream_error=stream_error)
        self.chat = SimpleNamespace(completions=self.completions)


def make_client(
    stream_error: OpenAIError | None = None,
) -> tuple[LLMClient, FakeSDKClient]:
    """Create an LLM client backed by a deterministic compatible SDK."""
    sdk = FakeSDKClient(stream_error=stream_error)
    settings = LLMSettings(
        _env_file=None,
        api_key=SecretStr("test-key"),
        base_url="https://compatible.example/v1",
        model="compatible-model",
        extra_body={"vendor_option": True},
    )
    return LLMClient(settings, client=sdk), sdk


def test_complete_uses_compatible_request_shape() -> None:
    """Complete calls must use only compatible fields plus opaque extensions."""
    client, sdk = make_client()

    assert client.complete("hello") == "complete"
    assert sdk.completions.calls == [
        {
            "model": "compatible-model",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": False,
            "extra_body": {"vendor_option": True},
        }
    ]


def test_complete_messages_preserves_system_and_user_roles() -> None:
    """RAG callers can send structured messages without flattening roles."""
    client, sdk = make_client()
    messages: list[LLMMessage] = [
        {"role": "system", "content": "use only context"},
        {"role": "user", "content": "context and question"},
    ]

    assert client.complete_messages(messages) == "complete"
    assert sdk.completions.calls[0]["messages"] == messages
    assert sdk.completions.calls[0]["stream"] is False


def test_stream_messages_preserves_roles_and_closes() -> None:
    """Structured streaming shares the request contract and cleanup path."""
    client, sdk = make_client()
    messages: list[LLMMessage] = [
        {"role": "system", "content": "rules"},
        {"role": "user", "content": "question"},
    ]

    assert list(client.stream_messages(messages)) == ["A", "B"]
    assert sdk.completions.calls[0]["messages"] == messages
    assert sdk.completions.calls[0]["stream"] is True
    assert sdk.completions.stream_response.closed is True


@pytest.mark.parametrize(
    "messages",
    [
        [],
        [{"role": "tool", "content": "invalid"}],
        [{"role": "user", "content": "   "}],
    ],
)
def test_messages_reject_empty_or_invalid_values(messages: list[Any]) -> None:
    """Invalid structured input fails before the compatible SDK is called."""
    client, sdk = make_client()

    with pytest.raises(ValueError):
        client.complete_messages(messages)  # type: ignore[arg-type]

    assert sdk.completions.calls == []


def test_complete_rejects_empty_upstream_content() -> None:
    """An empty complete response cannot become a successful RAG answer."""
    client, sdk = make_client()

    def empty_response(**kwargs: Any) -> Any:
        sdk.completions.calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=None))]
        )

    sdk.completions.create = empty_response  # type: ignore[method-assign]

    with pytest.raises(LLMServiceError, match="empty response"):
        client.complete_messages([{"role": "user", "content": "question"}])


def test_stream_yields_only_text_deltas() -> None:
    """Streams must ignore empty deltas and close after normal completion."""
    client, sdk = make_client()

    assert list(client.stream("hello")) == ["A", "B"]
    assert sdk.completions.calls[0]["stream"] is True
    assert sdk.completions.stream_response.closed is True


def test_stream_closes_when_consumer_stops_early() -> None:
    """Closing the application iterator must close the upstream stream."""
    client, sdk = make_client()
    stream = client.stream("hello")

    assert next(stream) == "A"
    stream.close()

    assert sdk.completions.stream_response.closed is True


def test_stream_closes_when_upstream_fails() -> None:
    """An upstream SDK error must be mapped and still release its stream."""
    client, sdk = make_client(stream_error=OpenAIError("upstream failed"))

    with pytest.raises(LLMServiceError, match="stream failed"):
        list(client.stream("hello"))

    assert sdk.completions.stream_response.closed is True


def test_llm_api_key_is_redacted_in_settings_repr() -> None:
    """SecretStr must prevent accidental key disclosure in diagnostics."""
    settings = LLMSettings(
        _env_file=None,
        api_key=SecretStr("super-secret-key"),
    )

    assert "super-secret-key" not in repr(settings)
