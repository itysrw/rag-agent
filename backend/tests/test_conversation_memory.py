"""Complete-turn transactions, bounded ordered history and process-local isolation."""

from collections.abc import Iterator
from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.config import ConversationMemorySettings
from backend.app.core.database import Base, DatabaseConfigurationError
from backend.app.models.conversation import Conversation
from backend.app.models.message import ConversationMessage
from backend.app.services.conversation_memory import (
    ConversationBusyError, ConversationHistoryMessage as Message, ConversationMemoryError,
    ConversationMemoryService, ConversationMemoryUnavailableError, ConversationNotFoundError,
    ConversationSource, acquire_conversation, history_token_count, serialize_history, truncate_history,
)
from backend.app.services.rag import RAGSource


@pytest.fixture
def memory_store() -> Iterator[tuple[ConversationMemoryService, sessionmaker[Session]]]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    yield ConversationMemoryService(factory), factory
    engine.dispose()


@pytest.mark.parametrize("turns", [0, 1, 5, 6])
def test_reads_latest_five_complete_turns_in_order(memory_store, turns: int) -> None:
    memory, factory = memory_store
    snapshot = memory.open_session(None)
    assert snapshot.history == ()
    for i in range(turns):
        memory.append_turn(session_id=snapshot.session_id, user_message=f"question {i}",
                           assistant_message=f"answer {i}", sources=[RAGSource("制度.pdf", i + 1)])
    result = memory.open_session(snapshot.session_id)
    assert [m.content for m in result.history] == [text for i in range(max(0, turns - 5), turns)
                                                for text in (f"question {i}", f"answer {i}")]
    assert len(result.history) == min(turns, 5) * 2
    if turns:
        assert result.history[-1].sources == (ConversationSource("制度.pdf", turns),)
    with factory() as session:
        rows = session.scalars(select(ConversationMessage).order_by(ConversationMessage.sequence_no)).all()
        assert len(rows) == turns * 2
        assert all(row.message_metadata == {} if row.role == "user"
                   else set(row.message_metadata) == {"sources"} for row in rows)
        assert session.get(Conversation, snapshot.session_id).updated_at is not None


def test_unknown_session_and_isolation(memory_store) -> None:
    memory, _ = memory_store
    a, b = memory.open_session(None), memory.open_session(None)
    memory.append_turn(session_id=a.session_id, user_message="private A", assistant_message="answer A", sources=[])
    assert memory.open_session(b.session_id).history == ()
    with pytest.raises(ConversationNotFoundError):
        memory.open_session(uuid4())
    with pytest.raises(ConversationNotFoundError):
        memory.append_turn(session_id=uuid4(), user_message="q", assistant_message="a", sources=[])


def test_second_message_failure_rolls_back_whole_turn_and_updated_at(memory_store) -> None:
    memory, factory = memory_store
    snapshot = memory.open_session(None)
    with factory() as session:
        before = session.get(Conversation, snapshot.session_id).updated_at

    def fail_assistant(mapper, connection, target) -> None:
        if target.role == "assistant":
            raise SQLAlchemyError("private database diagnostic")

    event.listen(ConversationMessage, "before_insert", fail_assistant)
    try:
        with pytest.raises(ConversationMemoryError) as error:
            memory.append_turn(session_id=snapshot.session_id, user_message="full question",
                               assistant_message="full answer", sources=[])
        assert "private" not in str(error.value)
    finally:
        event.remove(ConversationMessage, "before_insert", fail_assistant)
    with factory() as session:
        assert session.query(ConversationMessage).count() == 0
        assert session.get(Conversation, snapshot.session_id).updated_at == before


@pytest.mark.parametrize("failure, expected", [
    (DatabaseConfigurationError("secret"), ConversationMemoryUnavailableError),
    (OperationalError("private SQL", {}, Exception("secret")), ConversationMemoryUnavailableError),
    (TimeoutError("secret"), ConversationMemoryUnavailableError),
    (SQLAlchemyError("secret"), ConversationMemoryError),
])
def test_memory_errors_are_classified_without_sensitive_details(failure, expected) -> None:
    calls = []
    def factory():
        calls.append(True)
        raise failure
    memory = ConversationMemoryService(factory)
    assert calls == []
    with pytest.raises(expected) as error:
        memory.open_session(None)
    assert calls == [True] and "secret" not in str(error.value) and "private" not in str(error.value)


def history(turns: int, text: str = "answer") -> tuple[Message, ...]:
    return tuple(m for i in range(turns) for m in (
        Message("user", f"question {i}"), Message("assistant", f"{i}: {text}", (ConversationSource("员工手册.pdf", 12),)),
    ))


def test_turn_limit_priority_and_exact_json_token_budget() -> None:
    source = history(6)
    assert truncate_history(source) == source[-10:]
    budget = history_token_count(source[-4:])
    assert truncate_history(source, max_tokens=budget) == source[-4:]
    assert history_token_count(truncate_history(source, max_tokens=budget - 1)) <= budget - 1


@pytest.mark.parametrize("text", ["中文很长\n" * 1000, "👩🏽‍💻🦊" * 1000, "<|endoftext|>" * 1000],
                         ids=["chinese", "emoji", "special-token-text"])
def test_oversized_latest_turn_is_valid_unicode_json_and_counted_with_sources(text: str) -> None:
    import json
    source = (Message("user", text), Message("assistant", text, (ConversationSource("第1页.pdf", 2),)))
    clipped = truncate_history(source, max_tokens=128)
    assert len(clipped) == 2 and clipped[1].sources == source[1].sources
    assert history_token_count(clipped) <= 128
    assert json.loads(serialize_history(clipped))[1]["sources"] == [{"filename": "第1页.pdf", "page": 2}]
    for message in clipped:
        assert "\ufffd" not in message.content
        message.content.encode("utf-8")
    assert source[0].content == text  # Stored DTOs are never shortened in place.


def test_large_source_metadata_is_bounded_without_fabricating_filenames() -> None:
    sources = tuple(ConversationSource("员工手册" * 200 + str(i) + ".pdf", i + 1) for i in range(5))
    clipped = truncate_history((Message("user", "q"), Message("assistant", "a", sources)), max_tokens=128)
    assert history_token_count(clipped) <= 128
    assert all(source in sources for source in clipped[1].sources)


@pytest.mark.parametrize("bad", [(Message("user", "q"),), (Message("assistant", "a"), Message("user", "q"))])
def test_partial_or_reversed_turn_is_rejected(bad) -> None:
    with pytest.raises(ConversationMemoryError):
        truncate_history(bad)


def test_incomplete_persisted_turn_is_rejected(memory_store) -> None:
    memory, factory = memory_store
    snapshot = memory.open_session(None)
    with factory() as session, session.begin():
        session.add(ConversationMessage(conversation_id=snapshot.session_id, sequence_no=1,
                                        role="user", content="orphan"))
    with pytest.raises(ConversationMemoryError):
        memory.open_session(snapshot.session_id)


def test_process_local_conflict_and_independent_sessions() -> None:
    a, b = uuid4(), uuid4()
    lease = acquire_conversation(a)
    try:
        with pytest.raises(ConversationBusyError):
            acquire_conversation(a)
        acquire_conversation(b).close()
    finally:
        lease.close()
        lease.close()
    acquire_conversation(a).close()


def test_memory_settings_defaults_and_bounds() -> None:
    from pydantic import ValidationError
    settings = ConversationMemorySettings(_env_file=None)
    assert (settings.max_turns, settings.max_tokens, settings.encoding_name) == (5, 2000, "o200k_base")
    for values in ({"max_turns": 6}, {"max_tokens": 0}, {"encoding_name": "unknown"}):
        with pytest.raises(ValidationError):
            ConversationMemorySettings(_env_file=None, **values)


def test_memory_environment_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MEMORY_MAX_TURNS", "5")
    monkeypatch.setenv("MEMORY_MAX_TOKENS", "256")
    monkeypatch.setenv("MEMORY_ENCODING_NAME", "o200k_base")
    configured = ConversationMemorySettings(_env_file=None)
    assert configured.max_turns == 5 and configured.max_tokens == 256
