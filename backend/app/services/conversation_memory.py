"""PostgreSQL business messages, bounded prompt history and process-local leases."""

from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, replace
from functools import lru_cache
import json
from threading import Lock
from typing import Literal, TYPE_CHECKING
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError, DisconnectionError, InterfaceError, OperationalError, SQLAlchemyError
from sqlalchemy.exc import TimeoutError as SQLTimeoutError
from sqlalchemy.orm import Session
import tiktoken

from backend.app.core.database import DatabaseConfigurationError, get_session_factory
from backend.app.models.conversation import Conversation
from backend.app.models.document import utc_now
from backend.app.models.message import ConversationMessage

if TYPE_CHECKING:
    from backend.app.services.rag import RAGSource


class ConversationMemoryError(RuntimeError):
    """Safe internal read/write failure."""


class ConversationMemoryUnavailableError(ConversationMemoryError):
    """Database configuration, connection or timeout failure."""


class ConversationNotFoundError(ConversationMemoryError):
    """The supplied session does not exist."""


class ConversationBusyError(ConversationMemoryError):
    """Another request already owns this session in this process."""


class ConversationTurnCancelledError(ConversationMemoryError):
    """Cancellation observed before commit rolls the entire turn back."""


@dataclass(frozen=True, slots=True)
class ConversationSource:
    filename: str
    page: int


@dataclass(frozen=True, slots=True)
class ConversationHistoryMessage:
    role: Literal["user", "assistant"]
    content: str
    sources: tuple[ConversationSource, ...] = ()


@dataclass(frozen=True, slots=True)
class ConversationSnapshot:
    session_id: UUID
    history: tuple[ConversationHistoryMessage, ...]


def validate_history(history: Sequence[ConversationHistoryMessage]) -> None:
    """Reject partial, misordered or malformed turns before constructing prompts."""
    if isinstance(history, (str, bytes)) or len(history) % 2:
        raise ConversationMemoryError("The conversation history is invalid.")
    for index, message in enumerate(history):
        if (not isinstance(message, ConversationHistoryMessage)
                or message.role != ("user" if index % 2 == 0 else "assistant")
                or not isinstance(message.content, str) or not isinstance(message.sources, tuple)
                or (message.role == "user" and message.sources)):
            raise ConversationMemoryError("The conversation history is invalid.")
        for source in message.sources:
            if (not isinstance(source, ConversationSource) or not isinstance(source.filename, str)
                    or not source.filename.strip() or type(source.page) is not int or source.page < 1):
                raise ConversationMemoryError("The conversation history is invalid.")


def history_payload(history: Sequence[ConversationHistoryMessage]) -> list[dict[str, object]]:
    """Serialize only business message text and backend-derived sources."""
    validate_history(history)
    return [{"role": m.role, "content": m.content,
             "sources": [{"filename": s.filename, "page": s.page} for s in m.sources]}
            for m in history]


def serialize_history(history: Sequence[ConversationHistoryMessage]) -> str:
    """Use the same compact JSON representation for counting and prompts."""
    return json.dumps(history_payload(history), ensure_ascii=False, separators=(",", ":"))


def history_token_count(history: Sequence[ConversationHistoryMessage], encoding_name: str = "o200k_base") -> int:
    """Count role/content/sources and their JSON envelope, using the pinned encoding."""
    return len(tiktoken.get_encoding(encoding_name).encode(serialize_history(history), disallowed_special=()))


def truncate_history(
    history: Sequence[ConversationHistoryMessage], *, max_turns: int = 5,
    max_tokens: int = 2000, encoding_name: str = "o200k_base",
) -> tuple[ConversationHistoryMessage, ...]:
    """Prefer recent whole turns; shorten only an oversized latest turn."""
    validate_history(history)
    if type(max_turns) is not int or not 1 <= max_turns <= 5 or type(max_tokens) is not int or max_tokens < 1:
        raise ValueError("Invalid conversation history limits.")
    recent = tuple(history[-2 * max_turns:])
    if not recent:
        return ()
    encoding = tiktoken.get_encoding(encoding_name)

    def size(items: Sequence[ConversationHistoryMessage]) -> int:
        return len(encoding.encode(serialize_history(items), disallowed_special=()))

    selected: tuple[ConversationHistoryMessage, ...] = ()
    for index in range(len(recent) - 2, -1, -2):
        candidate = recent[index:index + 2] + selected
        if size(candidate) > max_tokens:
            break
        selected = candidate
    if selected or not recent:
        return selected

    pair = [replace(m, content="") for m in recent[-2:]]
    # Preserve whole, truthful source entries; never invent a shortened filename.
    while pair[1].sources and size(pair) + 4 > max_tokens:
        pair[1] = replace(pair[1], sources=pair[1].sources[:-1])
    if size(pair) + 4 > max_tokens:
        raise ValueError("The history budget cannot contain a complete turn envelope.")
    tokens = [encoding.encode(m.content, disallowed_special=()) for m in recent[-2:]]
    available = max_tokens - size(pair)
    lengths = [min(len(tokens[0]), available // 2), 0]
    lengths[1] = min(len(tokens[1]), available - lengths[0])

    def prefix(values: list[int], count: int) -> str:
        while count:
            try:
                return encoding.decode(values[:count], errors="strict")
            except UnicodeDecodeError:
                count -= 1
        return ""

    while True:
        clipped = tuple(replace(m, content=prefix(t, n)) for m, t, n in zip(pair, tokens, lengths, strict=True))
        excess = size(clipped) - max_tokens
        if excess <= 0:
            return clipped
        largest = 0 if lengths[0] >= lengths[1] else 1
        lengths[largest] = max(0, lengths[largest] - max(1, excess))


class ConversationLease:
    """Release a session once, even across response worker threads."""

    def __init__(self, session_id: UUID, release: Callable[[UUID], None]) -> None:
        self.session_id = session_id
        self._release = release
        self._lock = Lock()
        self._closed = False

    def close(self) -> None:
        """Drop the process-local ownership without retaining idle UUIDs."""
        with self._lock:
            if not self._closed:
                self._closed = True
                self._release(self.session_id)


_active_sessions: set[UUID] = set()
_active_lock = Lock()


def acquire_conversation(session_id: UUID) -> ConversationLease:
    """Claim a session non-blockingly; this is not a distributed worker lock."""
    with _active_lock:
        if session_id in _active_sessions:
            raise ConversationBusyError("The conversation already has a request in progress.")
        _active_sessions.add(session_id)

    def release(value: UUID) -> None:
        with _active_lock:
            _active_sessions.discard(value)

    return ConversationLease(session_id, release)


class ConversationMemoryService:
    """Read DTOs then close the Session before any model/tool work starts."""

    def __init__(self, session_factory: Callable[[], Session] | None = None) -> None:
        self._session_factory = session_factory

    @contextmanager
    def _session(self) -> Iterator[Session]:
        try:
            with (self._session_factory or get_session_factory())() as session:
                yield session
        except (DatabaseConfigurationError, ValidationError, OperationalError, InterfaceError,
                DisconnectionError, SQLTimeoutError, TimeoutError) as exc:
            raise ConversationMemoryUnavailableError("The conversation memory is unavailable.") from exc
        except DBAPIError as exc:
            error = ConversationMemoryUnavailableError if exc.connection_invalidated else ConversationMemoryError
            raise error("The conversation memory request failed.") from exc
        except SQLAlchemyError as exc:
            raise ConversationMemoryError("The conversation memory request failed.") from exc

    def open_session(self, session_id: UUID | None) -> ConversationSnapshot:
        """Create an empty session or load exactly its latest five complete turns."""
        if session_id is not None and not isinstance(session_id, UUID):
            raise ValueError("session_id must be a UUID or None")
        with self._session() as session:
            if session_id is None:
                with session.begin():
                    conversation = Conversation()
                    session.add(conversation)
                    session.flush()
                    session_id = conversation.id
                return ConversationSnapshot(session_id, ())
            if session.get(Conversation, session_id) is None:
                raise ConversationNotFoundError("The conversation does not exist.")
            rows = session.scalars(select(ConversationMessage)
                                   .where(ConversationMessage.conversation_id == session_id)
                                   .order_by(ConversationMessage.sequence_no.desc()).limit(10)).all()
            rows.reverse()
            if rows and (rows[0].sequence_no % 2 != 1 or any(
                row.sequence_no != rows[0].sequence_no + i for i, row in enumerate(rows)
            )):
                raise ConversationMemoryError("The conversation history is invalid.")
            try:
                history = tuple(ConversationHistoryMessage(
                    row.role, row.content,
                    tuple(ConversationSource(**source) for source in row.message_metadata.get("sources", [])),
                ) for row in rows)
                validate_history(history)
            except (TypeError, ValueError, AttributeError) as exc:
                raise ConversationMemoryError("The conversation history is invalid.") from exc
            return ConversationSnapshot(session_id, history)

    def append_turn(
        self, *, session_id: UUID, user_message: str, assistant_message: str,
        sources: Sequence["RAGSource"],
        is_cancelled: Callable[[], bool] | None = None,
    ) -> None:
        """Commit two full messages and updated_at together, or roll everything back."""
        if (not isinstance(session_id, UUID) or not isinstance(user_message, str)
                or not user_message.strip() or not isinstance(assistant_message, str)
                or not assistant_message.strip()):
            raise ValueError("A complete conversation turn is required.")
        safe_sources = tuple(ConversationSource(s.filename, s.page) for s in sources)
        validate_history((ConversationHistoryMessage("user", user_message),
                          ConversationHistoryMessage("assistant", assistant_message, safe_sources)))
        with self._session() as session, session.begin():
            if is_cancelled is not None and is_cancelled():
                raise ConversationTurnCancelledError("The conversation turn was cancelled.")
            conversation = session.scalar(select(Conversation).where(Conversation.id == session_id).with_for_update())
            if conversation is None:
                raise ConversationNotFoundError("The conversation does not exist.")
            last = session.scalar(select(func.max(ConversationMessage.sequence_no))
                                  .where(ConversationMessage.conversation_id == session_id)) or 0
            if last % 2:
                raise ConversationMemoryError("The conversation history is invalid.")
            session.add_all([
                ConversationMessage(conversation_id=session_id, sequence_no=last + 1,
                                    role="user", content=user_message, message_metadata={}),
                ConversationMessage(conversation_id=session_id, sequence_no=last + 2,
                                    role="assistant", content=assistant_message,
                                    message_metadata={"sources": [{"filename": s.filename, "page": s.page}
                                                                   for s in safe_sources]}),
            ])
            conversation.updated_at = utc_now()
            session.flush()
            if is_cancelled is not None and is_cancelled():
                raise ConversationTurnCancelledError("The conversation turn was cancelled.")


@lru_cache
def get_conversation_memory_service() -> ConversationMemoryService:
    """Create a lazy adapter without reading database configuration."""
    return ConversationMemoryService()
