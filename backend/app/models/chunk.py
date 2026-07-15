"""Ordered, page-aware text chunks persisted for new documents."""

from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base

JSONScalar = str | int | float | bool | None


class Chunk(Base):
    """One deterministic token-bounded segment of a source document page."""

    __tablename__ = "chunks"
    __table_args__ = (
        UniqueConstraint("doc_id", "chunk_index", name="uq_chunks_doc_id_index"),
        CheckConstraint("chunk_index >= 0", name="ck_chunks_index_nonnegative"),
        CheckConstraint("page >= 1", name="ck_chunks_page_positive"),
        CheckConstraint(
            "length(trim(content)) > 0",
            name="ck_chunks_content_nonblank",
        ),
        Index("ix_chunks_doc_id", "doc_id"),
    )

    chunk_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    doc_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    page: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_metadata: Mapped[dict[str, JSONScalar]] = mapped_column(
        "metadata",
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
    )
