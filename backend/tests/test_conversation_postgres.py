"""Explicit opt-in PostgreSQL memory acceptance; never uses project dotenv."""

import os

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import DatabaseSettings
from backend.app.core.database import Base, build_database_url
from backend.app.models.conversation import Conversation
from backend.app.models.message import ConversationMessage
from backend.app.services.conversation_memory import ConversationMemoryService
from backend.app.services.rag import RAGSource

pytestmark = [pytest.mark.integration, pytest.mark.skipif(
    os.environ.get("RUN_CONVERSATION_POSTGRES_INTEGRATION") != "1",
    reason="enable RUN_CONVERSATION_POSTGRES_INTEGRATION with process PostgreSQL settings",
)]


def test_real_postgres_creates_memory_tables_and_persists_two_atomic_turns() -> None:
    """Create only missing memory tables and clean up only this test's session."""
    engine = create_engine(build_database_url(DatabaseSettings(_env_file=None)), pool_pre_ping=True)
    identity = None
    try:
        Base.metadata.create_all(engine, tables=[Conversation.__table__, ConversationMessage.__table__])
        factory = sessionmaker(engine, expire_on_commit=False)
        memory = ConversationMemoryService(factory)
        identity = memory.open_session(None).session_id
        for i in range(2):
            memory.append_turn(session_id=identity, user_message=f"synthetic question {i}",
                               assistant_message=f"synthetic answer {i}", sources=[RAGSource("synthetic.pdf", i + 1)])
        assert len(memory.open_session(identity).history) == 4
        with factory() as session:
            rows = session.scalars(select(ConversationMessage).where(
                ConversationMessage.conversation_id == identity).order_by(ConversationMessage.sequence_no)).all()
            assert [row.sequence_no for row in rows] == [1, 2, 3, 4]
            assert rows[-1].message_metadata == {"sources": [{"filename": "synthetic.pdf", "page": 2}]}
    finally:
        try:
            if identity is not None:
                with Session(engine) as session, session.begin():
                    session.delete(session.get(Conversation, identity))
        finally:
            engine.dispose()
