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
    from backend.app.services import rag, request_trace
    from backend.app.services.conversation_memory import ConversationMemoryService

    engines = []
    trace_sessions: sessionmaker | None = None

    def memory() -> ConversationMemoryService:
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        engines.append(engine)
        Base.metadata.create_all(engine)
        return ConversationMemoryService(sessionmaker(engine, expire_on_commit=False))

    def local_trace_sessions() -> sessionmaker:
        nonlocal trace_sessions
        if trace_sessions is None:
            engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
            engines.append(engine)
            Base.metadata.create_all(engine)
            trace_sessions = sessionmaker(engine, expire_on_commit=False)
        return trace_sessions

    monkeypatch.setattr(rag, "get_conversation_memory_service", memory)
    monkeypatch.setattr(request_trace, "get_session_factory", local_trace_sessions)
    yield
    for engine in engines:
        engine.dispose()
