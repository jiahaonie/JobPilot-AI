"""岗位描述分析的持久化生命周期。"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import JobAnalysisStatus

if TYPE_CHECKING:
    from app.models.job import Job


def utc_now() -> datetime:
    """返回供应用记录使用的带时区时间戳。"""
    return datetime.now(UTC)


class JobAnalysis(Base):
    """独立于岗位投递状态跟踪 JD 分析生命周期。"""

    __tablename__ = "job_analyses"

    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    status: Mapped[JobAnalysisStatus] = mapped_column(
        SqlEnum(
            JobAnalysisStatus,
            native_enum=False,
            values_callable=lambda statuses: [status.value for status in statuses],
        ),
        nullable=False,
        default=JobAnalysisStatus.PENDING,
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
    job: Mapped["Job"] = relationship(back_populates="analysis")
