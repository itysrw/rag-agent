"""Ordered user/assistant messages with safe source metadata only."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, JSON, Text, Uuid, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base
from backend.app.models.document import utc_now


class ConversationMessage(Base):
    """A message belongs to exactly one session and one monotonic position."""

    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("conversation_id", "sequence_no", name="uq_messages_conversation_sequence"),
        CheckConstraint("sequence_no >= 1", name="ck_messages_sequence_positive"),
        CheckConstraint("role IN ('user', 'assistant')", name="ck_messages_role"),
        CheckConstraint("length(trim(content)) > 0", name="ck_messages_content_nonblank"),
        Index("ix_messages_conversation_sequence", "conversation_id", "sequence_no"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False,
    )
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_metadata: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSON().with_variant(JSONB(), "postgresql"), nullable=False, default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
