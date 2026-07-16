"""Provider-neutral client for OpenAI-compatible chat APIs."""

from collections.abc import Iterator, Sequence
from functools import lru_cache
from typing import Any, Literal, Protocol, TypedDict

from openai import OpenAI, OpenAIError

from backend.app.core.config import LLMSettings, get_llm_settings


class OpenAICompatibleClient(Protocol):
    """Minimal SDK surface required by the application."""

    chat: Any


class LLMConfigurationError(RuntimeError):
    """Raised when the language model connection is not configured."""


class LLMServiceError(RuntimeError):
    """Raised when an OpenAI-compatible language model request fails."""


class LLMMessage(TypedDict):
    """One validated OpenAI-compatible chat message."""

    role: Literal["system", "user", "assistant"]
    content: str


class LLMClient:
    """Generate complete or streamed replies through a compatible API."""

    def __init__(
        self,
        settings: LLMSettings,
        client: OpenAICompatibleClient | None = None,
    ) -> None:
        if settings.api_key is None:
            raise LLMConfigurationError("LLM_API_KEY is not configured")

        api_key = settings.api_key.get_secret_value().strip()
        if not api_key or api_key == "your_api_key_here":
            raise LLMConfigurationError("LLM_API_KEY is not configured")

        self._settings = settings
        self._client = client or OpenAI(
            api_key=api_key,
            base_url=settings.base_url,
            timeout=settings.timeout_seconds,
        )

    @property
    def model(self) -> str:
        """Return the configured model identifier."""
        return self._settings.model

    def complete(self, message: str) -> str:
        """Return one complete reply for a legacy single-user message."""
        return self.complete_messages([{"role": "user", "content": message}])

    def complete_messages(self, messages: Sequence[LLMMessage]) -> str:
        """Return one complete assistant response for structured messages."""
        validated_messages = _validated_messages(messages)
        try:
            response = self._client.chat.completions.create(
                **self._request_options(messages=validated_messages, stream=False)
            )
        except OpenAIError as exc:
            raise LLMServiceError("The language model request failed") from exc

        content = response.choices[0].message.content
        if not isinstance(content, str) or not content:
            raise LLMServiceError("The language model returned an empty response")
        return content

    def stream(self, message: str) -> Iterator[str]:
        """Yield deltas for a legacy single-user message."""
        yield from self.stream_messages([{"role": "user", "content": message}])

    def stream_messages(self, messages: Sequence[LLMMessage]) -> Iterator[str]:
        """Yield text deltas for structured messages and close the upstream."""
        validated_messages = _validated_messages(messages)
        response: Any | None = None
        try:
            response = self._client.chat.completions.create(
                **self._request_options(messages=validated_messages, stream=True)
            )
            for chunk in response:
                content = chunk.choices[0].delta.content
                if isinstance(content, str) and content:
                    yield content
        except OpenAIError as exc:
            raise LLMServiceError("The language model stream failed") from exc
        finally:
            close = getattr(response, "close", None)
            if callable(close):
                close()

    def _request_options(
        self,
        *,
        messages: list[LLMMessage],
        stream: bool,
    ) -> dict[str, Any]:
        options: dict[str, Any] = {
            "model": self._settings.model,
            "messages": messages,
            "stream": stream,
        }
        if self._settings.extra_body:
            options["extra_body"] = self._settings.extra_body
        return options


def _validated_messages(messages: Sequence[LLMMessage]) -> list[LLMMessage]:
    if isinstance(messages, (str, bytes)) or not messages:
        raise ValueError("messages must be a nonempty sequence")

    validated: list[LLMMessage] = []
    allowed_roles = {"system", "user", "assistant"}
    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            raise ValueError(f"messages[{index}] must be an object")
        role = message.get("role")
        content = message.get("content")
        if role not in allowed_roles:
            raise ValueError(f"messages[{index}] has an invalid role")
        if not isinstance(content, str) or not content.strip():
            raise ValueError(f"messages[{index}] content must not be blank")
        validated.append({"role": role, "content": content})  # type: ignore[typeddict-item]
    return validated


@lru_cache
def get_llm_client() -> LLMClient:
    """Return the cached OpenAI-compatible language model client."""
    return LLMClient(get_llm_settings())
