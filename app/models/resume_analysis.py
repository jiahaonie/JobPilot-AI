"""简历技能提取的持久化生命周期。"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import ResumeAnalysisStatus

if TYPE_CHECKING:
    from app.models.resume import Resume


def utc_now() -> datetime:
    """返回供应用记录使用的带时区时间戳。"""
    return datetime.now(UTC)


class ResumeAnalysis(Base):
    """独立于简历持久化存储跟踪 LLM 分析。"""

    __tablename__ = "resume_analyses"

    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    status: Mapped[ResumeAnalysisStatus] = mapped_column(
        SqlEnum(
            ResumeAnalysisStatus,
            native_enum=False,
            values_callable=lambda statuses: [status.value for status in statuses],
        ),
        nullable=False,
        default=ResumeAnalysisStatus.PENDING,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    analyzed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
    resume: Mapped["Resume"] = relationship(back_populates="analysis")
