"""简历持久化模型。"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import ResumeAnalysisStatus

if TYPE_CHECKING:
    from app.models.job_resume import JobResume
    from app.models.resume_analysis import ResumeAnalysis


def utc_now() -> datetime:
    """返回供应用记录使用的带时区时间戳。"""
    return datetime.now(UTC)


class Resume(Base):
    """包含已提取技能列表的已保存简历。"""

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
    analysis: Mapped["ResumeAnalysis | None"] = relationship(
        back_populates="resume",
        cascade="all, delete-orphan",
        uselist=False,
    )
    job_bindings: Mapped[list["JobResume"]] = relationship(
        back_populates="resume",
        passive_deletes=True,
    )

    @property
    def analysis_status(self) -> ResumeAnalysisStatus:
        """公开生命周期状态，并将旧版简历视为已分析。"""
        return self.analysis.status if self.analysis else ResumeAnalysisStatus.READY

    @property
    def analysis_error(self) -> str | None:
        """返回最新且可安全展示的分析失败信息（若有）。"""
        return self.analysis.error_message if self.analysis else None

    @property
    def analyzed_at(self) -> datetime | None:
        """返回最近一次技能提取成功的时间。"""
        return self.analysis.analyzed_at if self.analysis else self.created_at
