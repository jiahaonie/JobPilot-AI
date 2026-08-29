"""Resume persistence model."""

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def utc_now() -> datetime:
    """Return a timezone-aware timestamp for application records."""

    return datetime.now(UTC)


class Resume(Base):
    """A saved resume with its extracted skill list."""

    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    skills: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
