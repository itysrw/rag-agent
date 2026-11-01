"""Isolated business-memory dependency for ordinary RAG/HTTP regression tests."""

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture(autouse=True)
def isolated_conversation_dependency(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Production still requires PostgreSQL; opt-in real integration keeps it real."""
    if request.node.get_closest_marker("integration"):
        yield
        return
    from backend.app.core.database import Base
    from backend.app.services import rag
    from backend.app.services.conversation_memory import ConversationMemoryService

    engines = []

    def memory() -> ConversationMemoryService:
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        engines.append(engine)
        Base.metadata.create_all(engine)
        return ConversationMemoryService(sessionmaker(engine, expire_on_commit=False))

    monkeypatch.setattr(rag, "get_conversation_memory_service", memory)
    yield
    for engine in engines:
        engine.dispose()
