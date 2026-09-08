"""持久化的结构化岗位要求。"""

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def utc_now() -> datetime:
    """返回供应用记录使用的带时区时间戳。"""
    return datetime.now(UTC)


class JobRequirementRow(Base):
    """单个岗位描述的最新结构化分析。"""

    __tablename__ = "job_requirements"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    job_title: Mapped[str] = mapped_column(String(200), nullable=False)
    extraction_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="job-requirements-v1",
    )
    skill_requirements: Mapped[list | None] = mapped_column(JSON, nullable=True)
    unscored_requirements: Mapped[list | None] = mapped_column(JSON, nullable=True)
    required_skills: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    preferred_skills: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    education: Mapped[str | None] = mapped_column(String(200), nullable=True)
    internship_duration: Mapped[str | None] = mapped_column(String(200), nullable=True)
    responsibilities: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    evidence: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
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
