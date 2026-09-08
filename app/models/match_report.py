"""简历岗位匹配结果的持久化不可变快照。"""

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def utc_now() -> datetime:
    """返回供应用记录使用的带时区时间戳。"""
    return datetime.now(UTC)


class MatchReportRow(Base):
    """关联岗位与简历的一份不可变匹配快照。"""

    __tablename__ = "match_reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_coverage_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    required_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    preferred_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_disclaimer: Mapped[str] = mapped_column(Text, nullable=False)
    matched_skills: Mapped[list] = mapped_column(JSON, nullable=False)
    bonus_skills: Mapped[list] = mapped_column(JSON, nullable=False)
    missing_skills: Mapped[list] = mapped_column(JSON, nullable=False)
    priority_skills: Mapped[list] = mapped_column(JSON, nullable=False)
    requirement_matches: Mapped[list | None] = mapped_column(JSON, nullable=True)
    required_skills_snapshot: Mapped[list] = mapped_column(JSON, nullable=False)
    preferred_skills_snapshot: Mapped[list] = mapped_column(JSON, nullable=False)
    resume_skills_snapshot: Mapped[list] = mapped_column(JSON, nullable=False)
    job_requirement_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    resume_analyzed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    scoring_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
