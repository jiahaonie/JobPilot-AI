"""岗位与当前选用简历之间的持久化关联。"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.job import Job
    from app.models.resume import Resume


def utc_now() -> datetime:
    """返回供应用记录使用的带时区时间戳。"""
    return datetime.now(UTC)


class JobResume(Base):
    """第一版中一个岗位唯一绑定的一份投递简历。"""

    __tablename__ = "job_resumes"
    __table_args__ = (
        UniqueConstraint("job_id", name="uq_job_resumes_job_id"),
        UniqueConstraint("job_id", "resume_id", name="uq_job_resumes_job_resume"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
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
    job: Mapped["Job"] = relationship(back_populates="resume_binding")
    resume: Mapped["Resume"] = relationship(back_populates="job_bindings")
