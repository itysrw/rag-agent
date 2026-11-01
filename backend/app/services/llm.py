"""Provider-neutral client for OpenAI-compatible chat APIs."""

from collections.abc import Iterator, Sequence
from copy import deepcopy
from functools import lru_cache
import json
from typing import Any, Literal, Protocol, TypedDict, cast
from uuid import UUID

from openai import OpenAI, OpenAIError

from backend.app.core.config import LLMSettings, get_llm_settings


class OpenAICompatibleClient(Protocol):
    """Minimal SDK surface required by the application."""

    chat: Any

    def with_options(self, *, max_retries: int) -> "OpenAICompatibleClient": ...


class LLMConfigurationError(RuntimeError):
    """Raised when the language model connection is not configured."""


class LLMServiceError(RuntimeError):
    """Raised when an OpenAI-compatible language model request fails."""


class LLMToolCallError(LLMServiceError):
    """The selector returned an unsafe or invalid function call."""


class QueryRewriteError(LLMServiceError):
    """A rewrite request or its bounded JSON output failed validation."""


ToolName = Literal["search_knowledge_base", "get_document_detail", "list_documents"]
TOOL_NAMES = frozenset({"search_knowledge_base", "get_document_detail", "list_documents"})
MAX_TOOL_ARGUMENT_BYTES = 65536


class LLMFunctionDefinition(TypedDict):
    """Provider-neutral function description and ordinary JSON Schema."""

    name: ToolName
    description: str
    parameters: dict[str, Any]


class LLMToolDefinition(TypedDict):
    """One compatible function tool; beta strict mode is not enabled."""

    type: Literal["function"]
    function: LLMFunctionDefinition


class AgentToolCall(TypedDict):
    """One locally validated, bounded call; never executed by the model."""

    call_id: str
    name: ToolName
    arguments: dict[str, str]


def validate_tool_call(value: object) -> AgentToolCall:
    """Validate again at the execution boundary, including calls from adapters."""
    invalid = "The language model returned an invalid tool call."
    if not isinstance(value, dict) or set(value) != {"call_id", "name", "arguments"}:
        raise LLMToolCallError(invalid)
    call_id, name, arguments = value["call_id"], value["name"], value["arguments"]
    if not isinstance(call_id, str) or not 1 <= len(call_id.strip()) <= 128:
        raise LLMToolCallError(invalid)
    if not isinstance(name, str) or name not in TOOL_NAMES or not isinstance(arguments, dict):
        raise LLMToolCallError(invalid)
    expected = {"query"} if name == "search_knowledge_base" else (
        {"doc_id"} if name == "get_document_detail" else set()
    )
    if set(arguments) != expected or any(not isinstance(v, str) for v in arguments.values()):
        raise LLMToolCallError(invalid)
    if name == "search_knowledge_base" and not 1 <= len(arguments["query"].strip()) <= 4096:
        raise LLMToolCallError(invalid)
    normalized = dict(arguments)
    if name == "get_document_detail":
        if not 1 <= len(arguments["doc_id"]) <= 64:
            raise LLMToolCallError(invalid)
        try:
            normalized["doc_id"] = str(UUID(arguments["doc_id"]))
        except ValueError as exc:
            raise LLMToolCallError(invalid) from exc
    try:
        if len(json.dumps(normalized, ensure_ascii=True).encode("utf-8")) > MAX_TOOL_ARGUMENT_BYTES:
            raise LLMToolCallError(invalid)
    except (ValueError, UnicodeError) as exc:
        raise LLMToolCallError(invalid) from exc
    return AgentToolCall(call_id=call_id.strip(), name=cast(ToolName, name), arguments=normalized)


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


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

    def select_tool(
        self, messages: Sequence[LLMMessage], tools: Sequence[LLMToolDefinition]
    ) -> AgentToolCall:
        """Request exactly one function without streaming or automatic SDK retries."""
        options = self._request_options(messages=_validated_messages(messages), stream=False)
        definitions = deepcopy(list(tools))
        if not definitions:
            raise ValueError("at least one tool definition is required")
        names = {tool["function"]["name"] for tool in definitions}
        if not names <= TOOL_NAMES or len(names) != len(definitions):
            raise ValueError("tool definitions must have unique allowed names")
        extra = deepcopy(options.get("extra_body", {}))
        # Extensions cannot override the controlled selector request.
        for key in ("tools", "tool_choice", "stream", "messages", "model", "parallel_tool_calls"):
            extra.pop(key, None)
        extra["thinking"] = {"type": "disabled"}
        options.update(tools=definitions, tool_choice="required", extra_body=extra)
        try:
            response = self._client.with_options(max_retries=0).chat.completions.create(**options)
        except OpenAIError as exc:
            raise LLMServiceError("The language model request failed") from exc
        choices = getattr(response, "choices", None)
        if not isinstance(choices, (list, tuple)) or len(choices) != 1:
            raise LLMToolCallError("The language model returned an invalid tool call.")
        message = getattr(choices[0], "message", None)
        calls = getattr(message, "tool_calls", None)
        if not isinstance(calls, (list, tuple)) or len(calls) != 1:
            raise LLMToolCallError("The language model must select exactly one tool.")
        call = calls[0]
        function = getattr(call, "function", None)
        raw = getattr(function, "arguments", None)
        try:
            if getattr(call, "type", None) != "function" or not isinstance(raw, str):
                raise ValueError("invalid function")
            if len(raw) > MAX_TOOL_ARGUMENT_BYTES or len(raw.encode("utf-8")) > MAX_TOOL_ARGUMENT_BYTES:
                raise ValueError("arguments too large")
            arguments = json.loads(raw, object_pairs_hook=_unique_json_object)
            parsed = validate_tool_call({"call_id": getattr(call, "id", None),
                                         "name": getattr(function, "name", None),
                                         "arguments": arguments})
            if parsed["name"] not in names:
                raise ValueError("tool not offered")
            return parsed
        except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
            raise LLMToolCallError("The language model returned an invalid tool call.") from exc

    def rewrite_query(self, messages: Sequence[LLMMessage]) -> str:
        """Resolve references once through bounded JSON output, without tools/retries."""
        options = self._request_options(messages=_validated_messages(messages), stream=False)
        extra = deepcopy(options.get("extra_body", {}))
        for key in ("tools", "tool_choice", "parallel_tool_calls", "stream", "messages",
                    "model", "response_format", "max_tokens", "max_completion_tokens"):
            extra.pop(key, None)
        extra["thinking"] = {"type": "disabled"}
        options.update(extra_body=extra, response_format={"type": "json_object"}, max_tokens=256)
        try:
            response = self._client.with_options(max_retries=0).chat.completions.create(**options)
            choices = getattr(response, "choices", None)
            if not isinstance(choices, (list, tuple)) or len(choices) != 1:
                raise ValueError("invalid choices")
            choice = choices[0]
            message = getattr(choice, "message", None)
            content = getattr(message, "content", None)
            if (getattr(choice, "finish_reason", None) != "stop"
                    or getattr(message, "tool_calls", None)
                    or not isinstance(content, str) or not content.strip()
                    or len(content.encode("utf-8")) > 65536):
                raise ValueError("invalid rewrite response")
            parsed = json.loads(content, object_pairs_hook=_unique_json_object)
            if not isinstance(parsed, dict) or set(parsed) != {"standalone_query"}:
                raise ValueError("invalid rewrite object")
            query = parsed["standalone_query"]
            if not isinstance(query, str) or not 1 <= len(query.strip()) <= 4096:
                raise ValueError("invalid rewrite question")
            query.encode("utf-8")
            return query.strip()
        except (OpenAIError, ValueError, TypeError, UnicodeError, RecursionError) as exc:
            raise QueryRewriteError("The query rewrite request failed.") from exc

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
