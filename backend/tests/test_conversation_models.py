"""Schema guarantees and explicit registration without a running PostgreSQL."""

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

from backend.app.core.database import Base
from backend.app.models.conversation import Conversation
from backend.app.models.message import ConversationMessage


def test_explicit_schema_registers_new_tables_without_altering_documents() -> None:
    from backend.app.models import init_db
    assert init_db.Conversation is Conversation
    assert init_db.ConversationMessage is ConversationMessage
    ddl = str(CreateTable(ConversationMessage.__table__).compile(dialect=postgresql.dialect()))
    assert "JSONB" in ddl and "ON DELETE CASCADE" in ddl
    assert "UNIQUE (conversation_id, sequence_no)" in ddl
    assert "role IN ('user', 'assistant')" in ddl
    assert {"conversations", "messages", "documents", "chunks"} <= set(Base.metadata.tables)
    assert Conversation.__table__.c.created_at.type.timezone
    assert Conversation.__table__.c.updated_at.type.timezone


@pytest.mark.parametrize("values", [
    {"role": "system", "content": "text", "sequence_no": 1},
    {"role": "user", "content": " ", "sequence_no": 1},
    {"role": "user", "content": "text", "sequence_no": 0},
])
def test_database_rejects_invalid_business_messages(values: dict[str, object]) -> None:
    engine = create_engine("sqlite://")
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            conversation = Conversation()
            session.add(conversation)
            session.flush()
            session.add(ConversationMessage(conversation_id=conversation.id, **values))
            with pytest.raises(IntegrityError):
                session.flush()
            session.rollback()
    finally:
        engine.dispose()


def test_duplicate_sequence_and_database_cascade() -> None:
    engine = create_engine("sqlite://")
    event.listen(engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as session, session.begin():
            conversation = Conversation()
            session.add(conversation)
            session.flush()
            identity = conversation.id
            session.add(ConversationMessage(conversation_id=identity, sequence_no=1, role="user", content="question"))
        with Session(engine) as session:
            session.add(ConversationMessage(conversation_id=identity, sequence_no=1, role="assistant", content="answer"))
            with pytest.raises(IntegrityError):
                session.commit()
        with Session(engine) as session, session.begin():
            session.delete(session.get(Conversation, identity))
        with Session(engine) as session:
            assert session.query(ConversationMessage).count() == 0
    finally:
        engine.dispose()
