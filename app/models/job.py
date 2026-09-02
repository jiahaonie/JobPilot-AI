"""岗位持久化模型。"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import JobAnalysisStatus, JobStatus

if TYPE_CHECKING:
    from app.models.job_analysis import JobAnalysis
    from app.models.job_resume import JobResume


def utc_now() -> datetime:
    """返回供应用记录使用的带时区时间戳。"""
    return datetime.now(UTC)


class Job(Base):
    """已保存的岗位描述及其用户管理的投递状态。"""

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    job_title: Mapped[str] = mapped_column(String(200), nullable=False)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    internship_duration: Mapped[str | None] = mapped_column(String(100), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1_000), nullable=True)
    status: Mapped[JobStatus | None] = mapped_column(
        SqlEnum(
            JobStatus,
            native_enum=False,
            values_callable=lambda statuses: [status.value for status in statuses],
        ),
        nullable=True,
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
    analysis: Mapped["JobAnalysis | None"] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        uselist=False,
    )
    resume_binding: Mapped["JobResume | None"] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        uselist=False,
    )

    @property
    def analysis_status(self) -> JobAnalysisStatus:
        """返回岗位分析状态，并兼容迁移前创建的内存对象。"""
        return self.analysis.status if self.analysis else JobAnalysisStatus.PENDING

    @property
    def analysis_error(self) -> str | None:
        """返回可安全展示的最近一次岗位分析错误。"""
        return self.analysis.error_message if self.analysis else None

    @property
    def analyzed_at(self) -> datetime | None:
        """返回最近一次岗位分析成功的时间。"""
        return self.analysis.analyzed_at if self.analysis else None

    @property
    def resume_id(self) -> int | None:
        """返回当前岗位绑定的投递简历编号。"""
        return self.resume_binding.resume_id if self.resume_binding else None
