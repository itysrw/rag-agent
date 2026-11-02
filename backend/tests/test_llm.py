"""Tests for the provider-neutral OpenAI-compatible client."""

from types import SimpleNamespace
from typing import Any

import pytest
from openai import OpenAIError
from pydantic import SecretStr

from backend.app.core.config import LLMSettings
from backend.app.services.llm import LLMClient, LLMMessage, LLMServiceError
from backend.app.services.llm import LLMToolCallError, MAX_TOOL_ARGUMENT_BYTES
from backend.app.services.llm import QueryRewriteError
from backend.app.agent.tools import tool_definitions


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
        self.retry_options: list[int] = []

    def with_options(self, *, max_retries: int) -> "FakeSDKClient":
        self.retry_options.append(max_retries)
        return self


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


def rewrite_response(content: Any = '{"standalone_query":"完整问题？"}', finish: str = "stop") -> Any:
    """One controlled JSON-output response with an explicit completion status."""
    return SimpleNamespace(choices=[SimpleNamespace(
        finish_reason=finish, message=SimpleNamespace(content=content),
    )])


def test_rewrite_uses_bounded_json_output_without_tools_or_retries() -> None:
    client, sdk = make_client()
    client._settings.extra_body.update({"tools": ["unsafe"], "stream": True,
                                        "response_format": {}, "max_tokens": 999999})
    calls = []
    def create(**options: Any) -> Any:
        calls.append(options)
        return rewrite_response()
    sdk.completions.create = create
    assert client.rewrite_query([{"role": "user", "content": "json question"}]) == "完整问题？"
    assert sdk.retry_options == [0] and len(calls) == 1
    options = calls[0]
    assert options["stream"] is False and options["max_tokens"] == 4096
    assert options["response_format"] == {"type": "json_object"}
    assert "tools" not in options and "tool_choice" not in options
    assert options["extra_body"] == {"vendor_option": True, "thinking": {"type": "disabled"}}


@pytest.mark.parametrize("content, finish", [
    (" ", "stop"), (None, "stop"), ("not json", "stop"), ("[]", "stop"),
    ("null", "stop"), ("{}", "stop"), ('{"standalone_query":2}', "stop"),
    ('{"standalone_query":" "}', "stop"),
    ('{"standalone_query":"q","extra":true}', "stop"),
    ('{"standalone_query":"q","standalone_query":"r"}', "stop"),
    ('{"standalone_query":"q"}', "length"), ('{"standalone_query":"q"}', "tool_calls"),
    ('{"standalone_query":"' + "q" * 4097 + '"}', "stop"),
    ('{"standalone_query":"\\ud800"}', "stop"),
])
def test_invalid_rewrite_never_retries_or_exposes_content(content: Any, finish: str) -> None:
    client, sdk = make_client()
    sdk.completions.create = lambda **_: rewrite_response(content, finish)
    with pytest.raises(QueryRewriteError, match="^The query rewrite request failed\\.$"):
        client.rewrite_query([{"role": "user", "content": "json question"}])
    assert sdk.retry_options == [0]


def test_rewrite_rejects_multiple_choices_and_upstream_failure() -> None:
    client, sdk = make_client()
    sdk.completions.create = lambda **_: SimpleNamespace(choices=[rewrite_response().choices[0]] * 2)
    with pytest.raises(QueryRewriteError):
        client.rewrite_query([{"role": "user", "content": "json question"}])
    def broken(**_: Any) -> Any:
        raise OpenAIError("private prompt or provider response")
    sdk.completions.create = broken
    with pytest.raises(QueryRewriteError) as error:
        client.rewrite_query([{"role": "user", "content": "json question"}])
    assert "private" not in str(error.value)


@pytest.mark.parametrize("length", [1, 4096])
def test_rewrite_accepts_question_length_boundaries(length: int) -> None:
    import json
    client, sdk = make_client()
    sdk.completions.create = lambda **_: rewrite_response(json.dumps({"standalone_query": "q" * length}))
    assert client.rewrite_query([{"role": "user", "content": "json question"}]) == "q" * length


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


def tool_response(name: str = "list_documents", arguments: Any = "{}", **changes: Any) -> Any:
    call = SimpleNamespace(id="call-1", type="function",
                           function=SimpleNamespace(name=name, arguments=arguments))
    for key, value in changes.items():
        setattr(call, key, value)
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=[call]))])


def selector_client(response: Any) -> tuple[LLMClient, FakeSDKClient]:
    client, sdk = make_client()
    def create(**kwargs: Any) -> Any:
        sdk.completions.calls.append(kwargs)
        if isinstance(response, Exception):
            raise response
        return response
    sdk.completions.create = create
    return client, sdk


@pytest.mark.parametrize(("name", "arguments", "parsed"), [
    ("list_documents", "{}", {}),
    ("search_knowledge_base", '{"query":"报销流程"}', {"query": "报销流程"}),
    ("get_document_detail", '{"doc_id":"AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE"}',
     {"doc_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"}),
])
def test_selector_uses_required_nonstreaming_single_call_without_retries(
    name: str, arguments: str, parsed: dict[str, str],
) -> None:
    client, sdk = selector_client(tool_response(name, arguments))
    definitions = tool_definitions()
    call = client.select_tool([{"role": "user", "content": "有哪些文档？"}], definitions)
    assert call == {"call_id": "call-1", "name": name, "arguments": parsed}
    options = sdk.completions.calls[0]
    assert options["stream"] is False and options["tool_choice"] == "required"
    assert options["model"] == "compatible-model" and options["tools"] == list(definitions)
    assert options["extra_body"] == {"vendor_option": True, "thinking": {"type": "disabled"}}
    assert sdk.retry_options == [0] and len(sdk.completions.calls) == 1
    assert all("strict" not in tool["function"] for tool in definitions)


@pytest.mark.parametrize("response", [
    None, SimpleNamespace(choices=[]), SimpleNamespace(choices=[SimpleNamespace(message=None)]),
    SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=[]))]),
    SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=[1, 2]))]),
    tool_response(type="other"), tool_response(id=""), tool_response(id="x" * 129),
    tool_response("unknown"), tool_response(arguments="not JSON private"),
    tool_response(arguments="[]"), tool_response(arguments='"private"'),
    tool_response(arguments="null"), tool_response(arguments={}),
    tool_response(arguments='{"extra":"private"}'),
    tool_response("search_knowledge_base", '{}'),
    tool_response("search_knowledge_base", '{"query":false}'),
    tool_response("search_knowledge_base", '{"query":"   "}'),
    tool_response("search_knowledge_base", '{"query":"a","query":"b"}'),
    tool_response("search_knowledge_base", '{"query":NaN}'),
    tool_response("get_document_detail", '{"doc_id":"private-invalid"}'),
    tool_response("list_documents", " " * (MAX_TOOL_ARGUMENT_BYTES + 1)),
    tool_response("list_documents", "[" * 1000 + "]" * 1000),
])
def test_selector_rejects_malformed_or_ambiguous_responses_without_retry(response: Any) -> None:
    client, sdk = selector_client(response)
    with pytest.raises(LLMToolCallError) as error:
        client.select_tool([{"role": "user", "content": "question"}], tool_definitions())
    assert "private" not in str(error.value)
    assert len(sdk.completions.calls) == 1 and sdk.retry_options == [0]


def test_selector_sdk_failure_is_safe_and_not_retried() -> None:
    client, sdk = selector_client(OpenAIError("private upstream"))
    with pytest.raises(LLMServiceError) as error:
        client.select_tool([{"role": "user", "content": "question"}], tool_definitions())
    assert "private" not in str(error.value)
    assert len(sdk.completions.calls) == 1 and sdk.retry_options == [0]


@pytest.mark.parametrize("character", ["中", "\U0001f642"])
def test_selector_accepts_full_4096_character_unicode_query(character: str) -> None:
    import json
    query = character * 4096
    client, _ = selector_client(tool_response("search_knowledge_base", json.dumps({"query": query})))
    assert client.select_tool([{"role": "user", "content": query}], tool_definitions())["arguments"] == {"query": query}


def test_selector_cannot_be_overridden_by_extra_body_and_does_not_change_generation() -> None:
    client, sdk = selector_client(tool_response())
    client._settings.extra_body.update(tool_choice="none", tools=[], stream=True,
                                      thinking={"type": "enabled"})
    client.select_tool([{"role": "user", "content": "question"}], tool_definitions())
    options = sdk.completions.calls[0]
    assert options["tool_choice"] == "required" and options["stream"] is False
    assert "tools" not in options["extra_body"] and "stream" not in options["extra_body"]
    assert options["extra_body"]["thinking"] == {"type": "disabled"}
    assert client._settings.extra_body["thinking"] == {"type": "enabled"}
    assert "tools" not in client._request_options(messages=[{"role": "user", "content": "q"}], stream=False)
