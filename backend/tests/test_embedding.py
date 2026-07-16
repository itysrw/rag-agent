"""Unit tests for pinned local BGE embedding and the read-only command."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from io import StringIO
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
from huggingface_hub.errors import HfHubHTTPError, LocalEntryNotFoundError
from pydantic import ValidationError
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import backend.app.commands.embed_document as embed_document_command
from backend.app.commands.embed_document import (
    DocumentChunksNotFoundError,
    embed_document,
    print_summary,
)
from backend.app.core.config import (
    EMBEDDING_MODEL_REVISION,
    PROJECT_ROOT,
    EmbeddingSettings,
    get_embedding_settings,
)
from backend.app.core.database import Base
from backend.app.models.chunk import Chunk
from backend.app.models.document import Document
from backend.app.services.embedding import (
    BGE_QUERY_INSTRUCTION,
    ChunkEmbeddingInput,
    ChunkEmbeddingInputTooLongError,
    EmbeddingClient,
    EmbeddingError,
    EmbeddingInputError,
    EmbeddingInputTooLongError,
    EmbeddingResultError,
    ModelDownloadError,
    embed_chunks,
    ensure_model_snapshot,
    get_embedding_client,
    validate_model_input_length,
)


def build_settings(tmp_path: Path, **overrides: Any) -> EmbeddingSettings:
    """Build isolated settings without loading a repository environment file."""
    return EmbeddingSettings(
        _env_file=None,
        cache_dir=tmp_path,
        **overrides,
    )


class FakeTokenizer:
    """Count one token per character plus two BERT special tokens."""

    def encode(
        self,
        text: str,
        *,
        add_special_tokens: bool,
        truncation: bool,
    ) -> list[int]:
        assert add_special_tokens is True
        assert truncation is False
        return list(range(len(text) + 2))


class FakeModel:
    """Return deterministic normalized basis vectors and record each batch."""

    def __init__(
        self,
        *,
        dimension: int = 512,
        max_seq_length: int = 512,
        output_factory: Callable[[list[str]], Any] | None = None,
    ) -> None:
        self.dimension = dimension
        self.max_seq_length = max_seq_length
        self.tokenizer = FakeTokenizer()
        self.output_factory = output_factory
        self.batches: list[list[str]] = []
        self.encode_kwargs: list[dict[str, Any]] = []
        self.encoded_count = 0

    def get_sentence_embedding_dimension(self) -> int:
        return self.dimension

    def encode(self, sentences: list[str], **kwargs: Any) -> Any:
        batch = list(sentences)
        self.batches.append(batch)
        self.encode_kwargs.append(kwargs)
        if self.output_factory is not None:
            return self.output_factory(batch)

        vectors: list[list[float]] = []
        for _ in batch:
            vector = [0.0] * self.dimension
            vector[self.encoded_count % self.dimension] = 1.0
            vectors.append(vector)
            self.encoded_count += 1
        return vectors


def build_client(
    tmp_path: Path,
    model: FakeModel,
    **settings_overrides: Any,
) -> tuple[EmbeddingClient, list[Path]]:
    """Return a lazy client and a record of model-loader calls."""
    settings = build_settings(tmp_path, **settings_overrides)
    model_loads: list[Path] = []

    def load_model(path: Path, _: EmbeddingSettings) -> FakeModel:
        model_loads.append(path)
        return model

    return (
        EmbeddingClient(
            settings,
            snapshot_resolver=lambda _: tmp_path,
            model_loader=load_model,
        ),
        model_loads,
    )


def normalized_vector(dimension: int = 512) -> list[float]:
    """Return one finite unit vector."""
    return [1.0] + [0.0] * (dimension - 1)


def test_embedding_settings_are_pinned_and_need_no_api_key(tmp_path: Path) -> None:
    """Day 6 defaults are local, reproducible, and credential-free."""
    settings = build_settings(tmp_path)

    assert settings.model_name == "BAAI/bge-small-zh-v1.5"
    assert settings.model_revision == EMBEDDING_MODEL_REVISION
    assert settings.dimension == 512
    assert settings.batch_size == 32
    assert settings.device == "cpu"
    assert settings.normalize_embeddings is True
    assert settings.download_max_retries == 3
    assert not hasattr(settings, "api_key")


def test_embedding_cache_path_is_resolved_from_project_root() -> None:
    """Relative cache configuration does not depend on the current directory."""
    settings = EmbeddingSettings(_env_file=None, cache_dir=Path("data/test-models"))

    assert settings.cache_dir == (PROJECT_ROOT / "data" / "test-models").resolve()


def test_embedding_normalize_environment_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The documented EMBEDDING_NORMALIZE variable maps to the fixed setting."""
    monkeypatch.setenv("EMBEDDING_NORMALIZE", "true")

    settings = build_settings(tmp_path)

    assert settings.normalize_embeddings is True


@pytest.mark.parametrize(
    "overrides",
    [
        {"batch_size": 0},
        {"batch_size": 33},
        {"download_max_retries": -1},
        {"download_max_retries": 4},
        {"device": "cuda"},
        {"dimension": 384},
        {"normalize_embeddings": False},
        {"model_name": "another/model"},
        {"model_revision": "main"},
    ],
)
def test_embedding_settings_reject_unsupported_values(
    tmp_path: Path,
    overrides: dict[str, Any],
) -> None:
    """Configuration cannot silently expand beyond the fixed Day 6 contract."""
    with pytest.raises(ValidationError):
        build_settings(tmp_path, **overrides)


def test_empty_input_does_not_resolve_or_load_model(tmp_path: Path) -> None:
    """An empty batch returns immediately without model work."""
    called = False

    def fail_if_called(_: EmbeddingSettings) -> Path:
        nonlocal called
        called = True
        raise AssertionError("model snapshot must not be resolved")

    client = EmbeddingClient(
        build_settings(tmp_path),
        snapshot_resolver=fail_if_called,
    )

    assert client.embed_documents([]) == []
    assert called is False


@pytest.mark.parametrize(
    ("count", "expected_batches"),
    [
        (1, [1]),
        (32, [32]),
        (33, [32, 1]),
        (65, [32, 32, 1]),
    ],
)
def test_embedding_batches_never_exceed_32_and_preserve_order(
    tmp_path: Path,
    count: int,
    expected_batches: list[int],
) -> None:
    """Explicit outer batches preserve input order across boundaries."""
    model = FakeModel()
    client, model_loads = build_client(tmp_path, model)
    texts = [f"text-{index}" for index in range(count)]

    vectors = client.embed_documents(texts)

    assert [len(batch) for batch in model.batches] == expected_batches
    assert [text for batch in model.batches for text in batch] == texts
    assert len(vectors) == count
    assert len(model_loads) == 1
    assert model.encode_kwargs[0]["batch_size"] == 32
    assert model.encode_kwargs[0]["normalize_embeddings"] is True
    assert "prompt" not in model.encode_kwargs[0]
    assert "prompt_name" not in model.encode_kwargs[0]


def test_client_reuses_one_loaded_model(tmp_path: Path) -> None:
    """Repeated inference calls reuse the same model instance."""
    client, model_loads = build_client(tmp_path, FakeModel())

    client.embed_documents(["first"])
    client.embed_documents(["second"])

    assert len(model_loads) == 1


def test_embed_query_applies_instruction_once_and_keeps_documents_plain(
    tmp_path: Path,
) -> None:
    """Only query vectors receive the fixed BGE retrieval instruction."""
    model = FakeModel()
    client, _ = build_client(tmp_path, model)

    query_vector = client.embed_query("  报销时间  ")
    document_vectors = client.embed_documents(["报销时间"])

    assert len(query_vector) == 512
    assert len(document_vectors[0]) == 512
    assert model.batches == [
        [f"{BGE_QUERY_INSTRUCTION}报销时间"],
        ["报销时间"],
    ]
    assert model.batches[0][0].count(BGE_QUERY_INSTRUCTION) == 1


def test_blank_query_fails_before_model_loading(tmp_path: Path) -> None:
    """Whitespace-only search input cannot trigger model work."""
    client, model_loads = build_client(tmp_path, FakeModel())

    with pytest.raises(EmbeddingInputError):
        client.embed_query("  \n  ")

    assert model_loads == []


def test_query_token_limit_includes_instruction_before_inference(
    tmp_path: Path,
) -> None:
    """The BGE query prefix participates in the no-truncation check."""
    model = FakeModel(max_seq_length=len(BGE_QUERY_INSTRUCTION) + 2)
    client, _ = build_client(tmp_path, model)

    with pytest.raises(EmbeddingInputTooLongError) as error:
        client.embed_query("问题")

    assert error.value.input_index == 0
    assert error.value.token_count == len(BGE_QUERY_INSTRUCTION) + 4
    assert model.batches == []


@pytest.mark.parametrize("invalid", ["", " \n "])
def test_blank_input_fails_before_model_loading(tmp_path: Path, invalid: str) -> None:
    """Blank passages fail safely and do not trigger a model download."""
    client, model_loads = build_client(tmp_path, FakeModel())

    with pytest.raises(EmbeddingInputError) as error:
        client.embed_documents([invalid])

    assert len(model_loads) == 0
    assert str(error.value) == "input_index=0 embedding input must not be blank"


def test_string_is_not_accepted_as_a_text_sequence(tmp_path: Path) -> None:
    """A bare string cannot be accidentally embedded one character at a time."""
    client, _ = build_client(tmp_path, FakeModel())

    with pytest.raises(EmbeddingInputError):
        client.embed_documents("not-a-sequence")  # type: ignore[arg-type]


def test_bge_token_limit_includes_special_tokens_and_allows_boundary() -> None:
    """The tokenizer count includes specials and accepts exactly the limit."""
    model = FakeModel(max_seq_length=10)

    assert validate_model_input_length(model, "12345678") == 10


def test_overlong_input_stops_before_inference_and_hides_content(
    tmp_path: Path,
) -> None:
    """BGE overflow is explicit and never reaches silent model truncation."""
    secret_text = "private-passage"
    model = FakeModel(max_seq_length=10)
    client, _ = build_client(tmp_path, model)

    with pytest.raises(EmbeddingInputTooLongError) as error:
        client.embed_documents([secret_text])

    assert error.value.input_index == 0
    assert error.value.token_count == len(secret_text) + 2
    assert error.value.max_tokens == 10
    assert secret_text not in str(error.value)
    assert model.batches == []


@pytest.mark.parametrize("result_count", [1, 3])
def test_result_count_must_match_input_count(
    tmp_path: Path,
    result_count: int,
) -> None:
    """Too few or too many vectors fail before Chunk binding."""
    model = FakeModel(
        output_factory=lambda _: [normalized_vector() for _ in range(result_count)]
    )
    client, _ = build_client(tmp_path, model)

    with pytest.raises(EmbeddingResultError):
        client.embed_documents(["one", "two"])


@pytest.mark.parametrize("dimension", [511, 513])
def test_result_dimension_must_be_exactly_512(
    tmp_path: Path,
    dimension: int,
) -> None:
    """Wrong model output dimensions fail closed."""
    model = FakeModel(output_factory=lambda _: [normalized_vector(dimension)])
    client, _ = build_client(tmp_path, model)

    with pytest.raises(EmbeddingResultError):
        client.embed_documents(["one"])


@pytest.mark.parametrize("invalid_value", [float("nan"), float("inf"), -float("inf")])
def test_result_values_must_be_finite(
    tmp_path: Path,
    invalid_value: float,
) -> None:
    """NaN and infinity cannot reach later vector storage."""
    vector = normalized_vector()
    vector[0] = invalid_value
    model = FakeModel(output_factory=lambda _: [vector])
    client, _ = build_client(tmp_path, model)

    with pytest.raises(EmbeddingResultError):
        client.embed_documents(["one"])


def test_result_must_be_normalized(tmp_path: Path) -> None:
    """The client verifies the normalization requested from the model."""
    vector = [2.0] + [0.0] * 511
    model = FakeModel(output_factory=lambda _: [vector])
    client, _ = build_client(tmp_path, model)

    with pytest.raises(EmbeddingResultError):
        client.embed_documents(["one"])


def test_local_inference_error_is_not_retried(tmp_path: Path) -> None:
    """A deterministic local model failure is attempted exactly once."""
    attempts = 0

    def fail_inference(_: list[str]) -> list[list[float]]:
        nonlocal attempts
        attempts += 1
        raise RuntimeError("device failure")

    model = FakeModel(output_factory=fail_inference)
    client, _ = build_client(tmp_path, model)

    with pytest.raises(EmbeddingError):
        client.embed_documents(["one"])

    assert attempts == 1


def test_embed_chunks_preserves_chunk_identity_and_order(tmp_path: Path) -> None:
    """Vectors are rebound to UUIDs strictly by validated input position."""
    client, _ = build_client(tmp_path, FakeModel())
    chunk_ids = [uuid4(), uuid4(), uuid4()]
    chunks = [
        ChunkEmbeddingInput(chunk_id=chunk_id, content=f"text-{index}")
        for index, chunk_id in enumerate(chunk_ids)
    ]

    embedded = embed_chunks(chunks, client)

    assert [item.chunk_id for item in embedded] == chunk_ids
    assert embedded[0].vector[0] == 1.0
    assert embedded[1].vector[1] == 1.0
    assert embedded[2].vector[2] == 1.0


def test_embed_chunks_rejects_duplicate_ids_before_loading(tmp_path: Path) -> None:
    """Duplicate identities cannot create ambiguous vector bindings."""
    client, model_loads = build_client(tmp_path, FakeModel())
    chunk_id = uuid4()

    with pytest.raises(EmbeddingInputError):
        embed_chunks(
            [
                ChunkEmbeddingInput(chunk_id=chunk_id, content="first"),
                ChunkEmbeddingInput(chunk_id=chunk_id, content="second"),
            ],
            client,
        )

    assert model_loads == []


def test_chunk_length_error_contains_uuid_but_not_content(tmp_path: Path) -> None:
    """Chunk orchestration replaces the input index with a safe UUID."""
    client, _ = build_client(tmp_path, FakeModel(max_seq_length=10))
    chunk_id = uuid4()
    content = "private-passage"

    with pytest.raises(ChunkEmbeddingInputTooLongError) as error:
        embed_chunks(
            [ChunkEmbeddingInput(chunk_id=chunk_id, content=content)],
            client,
        )

    assert str(chunk_id) in str(error.value)
    assert content not in str(error.value)


class DownloadSequence:
    """Simulate a local cache miss followed by controlled network outcomes."""

    def __init__(self, outcomes: list[object]) -> None:
        self.outcomes = list(outcomes)
        self.local_calls = 0
        self.network_calls = 0

    def __call__(self, **kwargs: Any) -> str:
        if kwargs["local_files_only"]:
            self.local_calls += 1
            raise LocalEntryNotFoundError("not cached")
        self.network_calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return str(outcome)


def test_download_succeeds_without_retry(tmp_path: Path) -> None:
    """A first-attempt download does not sleep."""
    downloader = DownloadSequence([tmp_path])
    sleeps: list[float] = []

    result = ensure_model_snapshot(
        build_settings(tmp_path),
        downloader=downloader,
        sleep=sleeps.append,
    )

    assert result == tmp_path.resolve()
    assert downloader.local_calls == 1
    assert downloader.network_calls == 1
    assert sleeps == []


def test_transient_download_failures_use_one_two_four_second_backoff(
    tmp_path: Path,
) -> None:
    """Three transient failures are retried before the final success."""
    failures = [httpx.ConnectError("offline") for _ in range(3)]
    downloader = DownloadSequence([*failures, tmp_path])
    sleeps: list[float] = []

    result = ensure_model_snapshot(
        build_settings(tmp_path),
        downloader=downloader,
        sleep=sleeps.append,
    )

    assert result == tmp_path.resolve()
    assert downloader.network_calls == 4
    assert sleeps == [1.0, 2.0, 4.0]


def test_transient_download_failure_stops_after_three_retries(
    tmp_path: Path,
) -> None:
    """The initial attempt plus three retries is the hard network limit."""
    downloader = DownloadSequence(
        [httpx.ConnectError("offline") for _ in range(4)]
    )
    sleeps: list[float] = []

    with pytest.raises(ModelDownloadError):
        ensure_model_snapshot(
            build_settings(tmp_path),
            downloader=downloader,
            sleep=sleeps.append,
        )

    assert downloader.network_calls == 4
    assert sleeps == [1.0, 2.0, 4.0]


@pytest.mark.parametrize("failure_kind", ["timeout", "429", "503"])
def test_timeout_rate_limit_and_server_errors_are_retryable(
    tmp_path: Path,
    failure_kind: str,
) -> None:
    """Every approved transient failure class reaches a later success."""
    request = httpx.Request("GET", "https://huggingface.co/model")
    if failure_kind == "timeout":
        failure: BaseException = httpx.ReadTimeout("timed out", request=request)
    else:
        response = httpx.Response(int(failure_kind), request=request)
        failure = HfHubHTTPError("download failed", response=response)
    downloader = DownloadSequence([failure, tmp_path])
    sleeps: list[float] = []

    result = ensure_model_snapshot(
        build_settings(tmp_path),
        downloader=downloader,
        sleep=sleeps.append,
    )

    assert result == tmp_path.resolve()
    assert downloader.network_calls == 2
    assert sleeps == [1.0]


@pytest.mark.parametrize("status_code", [401, 403, 404])
def test_nonretryable_http_errors_fail_immediately(
    tmp_path: Path,
    status_code: int,
) -> None:
    """Authentication, permission, and missing-model errors are deterministic."""
    request = httpx.Request("GET", "https://huggingface.co/model")
    response = httpx.Response(status_code, request=request)
    downloader = DownloadSequence(
        [HfHubHTTPError("download failed", response=response)]
    )
    sleeps: list[float] = []

    with pytest.raises(ModelDownloadError):
        ensure_model_snapshot(
            build_settings(tmp_path),
            downloader=downloader,
            sleep=sleeps.append,
        )

    assert downloader.network_calls == 1
    assert sleeps == []


def test_invalid_cached_snapshot_does_not_trigger_network_retry(tmp_path: Path) -> None:
    """A corrupt local cache is not treated as a transient connection error."""
    network_called = False

    def corrupted_cache(**kwargs: Any) -> str:
        nonlocal network_called
        if not kwargs["local_files_only"]:
            network_called = True
        raise OSError("corrupt cache")

    with pytest.raises(ModelDownloadError):
        ensure_model_snapshot(
            build_settings(tmp_path),
            downloader=corrupted_cache,
            sleep=lambda _: None,
        )

    assert network_called is False


def test_cache_path_file_is_wrapped_before_download(tmp_path: Path) -> None:
    """A cache path that is a file becomes a safe model download error."""
    cache_file = tmp_path / "model-cache"
    cache_file.write_text("not a directory", encoding="utf-8")
    downloader_called = False

    def fail_if_called(**kwargs: Any) -> str:
        nonlocal downloader_called
        del kwargs
        downloader_called = True
        raise AssertionError("download must not be attempted")

    settings = EmbeddingSettings(_env_file=None, cache_dir=cache_file)

    with pytest.raises(ModelDownloadError) as error:
        ensure_model_snapshot(
            settings,
            downloader=fail_if_called,
            sleep=lambda _: None,
        )

    assert downloader_called is False
    assert str(cache_file) not in str(error.value)


@pytest.fixture
def chunk_database() -> Iterator[
    tuple[sessionmaker[Session], UUID, list[UUID]]
]:
    """Provide ordered Chunk rows in an isolated in-memory database."""
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    document_id = uuid4()
    chunk_ids = [uuid4(), uuid4()]
    with factory.begin() as session:
        session.add(
            Document(
                id=document_id,
                filename="notes.txt",
                size=7,
                status="ready",
                extracted_text="zero one",
            )
        )
        session.flush()
        session.add_all(
            [
                Chunk(
                    chunk_id=chunk_ids[1],
                    doc_id=document_id,
                    chunk_index=1,
                    content="one",
                    page=1,
                    chunk_metadata={"token_count": 1},
                ),
                Chunk(
                    chunk_id=chunk_ids[0],
                    doc_id=document_id,
                    chunk_index=0,
                    content="zero",
                    page=1,
                    chunk_metadata={"token_count": 1},
                ),
            ]
        )
    try:
        yield factory, document_id, chunk_ids
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_command_reads_chunks_in_index_order_without_writes(
    tmp_path: Path,
    chunk_database: tuple[sessionmaker[Session], UUID, list[UUID]],
) -> None:
    """The command reads ordered rows and leaves database state unchanged."""
    factory, document_id, _ = chunk_database
    model = FakeModel()
    client, _ = build_client(tmp_path, model)

    summary = embed_document(
        document_id,
        session_factory=factory,
        client_factory=lambda: client,
    )

    assert model.batches == [["zero", "one"]]
    assert summary.document_id == document_id
    assert summary.chunk_count == 2
    assert summary.embedding_dimension == 512
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(Chunk)) == 2


def test_command_without_chunks_fails_before_client_loading(
    chunk_database: tuple[sessionmaker[Session], UUID, list[UUID]],
) -> None:
    """Missing Chunks fail fast without loading the local model."""
    factory, _, _ = chunk_database
    client_called = False

    def fail_if_called() -> EmbeddingClient:
        nonlocal client_called
        client_called = True
        raise AssertionError("client must not be constructed")

    with pytest.raises(DocumentChunksNotFoundError):
        embed_document(
            uuid4(),
            session_factory=factory,
            client_factory=fail_if_called,
        )

    assert client_called is False


def test_command_summary_excludes_content_and_vector_values(
    tmp_path: Path,
    chunk_database: tuple[sessionmaker[Session], UUID, list[UUID]],
) -> None:
    """Successful output contains only the approved safe summary fields."""
    factory, document_id, _ = chunk_database
    client, _ = build_client(tmp_path, FakeModel())
    summary = embed_document(
        document_id,
        session_factory=factory,
        client_factory=lambda: client,
    )
    output = StringIO()

    print_summary(summary, output=output)
    rendered = output.getvalue()

    assert "model: BAAI/bge-small-zh-v1.5" in rendered
    assert "embedding_dimension: 512" in rendered
    assert "normalized: true" in rendered
    assert "status: success" in rendered
    assert "zero" not in rendered
    assert "one" not in rendered
    assert "[" not in rendered


def test_command_reports_embedding_configuration_error_separately_from_database(
    chunk_database: tuple[sessionmaker[Session], UUID, list[UUID]],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Invalid Embedding settings must not be reported as a database outage."""
    factory, document_id, _ = chunk_database
    monkeypatch.setattr(embed_document_command, "get_session_factory", lambda: factory)
    monkeypatch.setenv("EMBEDDING_BATCH_SIZE", "33")
    get_embedding_client.cache_clear()
    get_embedding_settings.cache_clear()
    try:
        exit_code = embed_document_command.main(
            ["--document-id", str(document_id)]
        )
    finally:
        get_embedding_client.cache_clear()
        get_embedding_settings.cache_clear()

    error_output = capsys.readouterr().err.lower()
    assert exit_code == 1
    assert "configuration" in error_output
    assert "database" not in error_output
