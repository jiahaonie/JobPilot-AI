"""Knowledge-document persistence model."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import DocumentStatus


def utc_now() -> datetime:
    """Return a timezone-aware timestamp for application records."""

    return datetime.now(UTC)


class KnowledgeDocument(Base):
    """Source document tracked while its chunks are indexed in Chroma."""

    __tablename__ = "knowledge_documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        SqlEnum(
            DocumentStatus,
            native_enum=False,
            values_callable=lambda statuses: [status.value for status in statuses],
        ),
        nullable=False,
        default=DocumentStatus.INDEXING,
        index=True,
    )
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
