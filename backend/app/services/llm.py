"""Provider-neutral client for OpenAI-compatible chat APIs."""

from collections.abc import Iterator
from functools import lru_cache
from typing import Any, Protocol

from openai import OpenAI, OpenAIError

from backend.app.core.config import LLMSettings, get_llm_settings


class OpenAICompatibleClient(Protocol):
    """Minimal SDK surface required by the application."""

    chat: Any


class LLMConfigurationError(RuntimeError):
    """Raised when the language model connection is not configured."""


class LLMServiceError(RuntimeError):
    """Raised when an OpenAI-compatible language model request fails."""


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
        """Return one complete assistant response."""
        try:
            response = self._client.chat.completions.create(
                **self._request_options(message=message, stream=False)
            )
        except OpenAIError as exc:
            raise LLMServiceError("The language model request failed") from exc

        content = response.choices[0].message.content
        if not content:
            raise LLMServiceError("The language model returned an empty response")
        return content

    def stream(self, message: str) -> Iterator[str]:
        """Yield text deltas from a streamed assistant response."""
        response: Any | None = None
        try:
            response = self._client.chat.completions.create(
                **self._request_options(message=message, stream=True)
            )
            for chunk in response:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        except OpenAIError as exc:
            raise LLMServiceError("The language model stream failed") from exc
        finally:
            close = getattr(response, "close", None)
            if callable(close):
                close()

    def _request_options(self, message: str, stream: bool) -> dict[str, Any]:
        options: dict[str, Any] = {
            "model": self._settings.model,
            "messages": [{"role": "user", "content": message}],
            "stream": stream,
        }
        if self._settings.extra_body:
            options["extra_body"] = self._settings.extra_body
        return options


@lru_cache
def get_llm_client() -> LLMClient:
    """Return the cached OpenAI-compatible language model client."""
    return LLMClient(get_llm_settings())
