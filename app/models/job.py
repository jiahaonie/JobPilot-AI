"""Job persistence model."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import JobStatus


def utc_now() -> datetime:
    """Return a timezone-aware timestamp for application records."""

    return datetime.now(UTC)


class Job(Base):
    """A saved job description and its user-managed application status."""

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    job_title: Mapped[str] = mapped_column(String(200), nullable=False)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    internship_duration: Mapped[str | None] = mapped_column(String(100), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1_000), nullable=True)
    status: Mapped[JobStatus] = mapped_column(
        SqlEnum(
            JobStatus,
            native_enum=False,
            values_callable=lambda statuses: [status.value for status in statuses],
        ),
        nullable=False,
        default=JobStatus.PENDING_ANALYSIS,
    )
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
