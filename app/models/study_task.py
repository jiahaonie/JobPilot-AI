"""学习任务持久化模型。"""

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import StudyTaskPhase, StudyTaskStatus

if TYPE_CHECKING:
    from app.models.study_plan import StudyPlan


def utc_now() -> datetime:
    """返回供应用记录使用的带时区时间戳。"""
    return datetime.now(UTC)


class StudyTask(Base):
    """由规则生成、由用户手动更新状态的学习任务。"""

    __tablename__ = "study_tasks"
    __table_args__ = (
        UniqueConstraint(
            "study_plan_id",
            "position",
            name="uq_study_tasks_plan_position",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    study_plan_id: Mapped[int] = mapped_column(
        ForeignKey("study_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill: Mapped[str] = mapped_column(String(200), nullable=False)
    phase: Mapped[StudyTaskPhase] = mapped_column(
        SqlEnum(
            StudyTaskPhase,
            native_enum=False,
            values_callable=lambda phases: [phase.value for phase in phases],
        ),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    learning_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    action: Mapped[str | None] = mapped_column(Text, nullable=True)
    completion_criteria: Mapped[str] = mapped_column(Text, nullable=False)
    resource_query: Mapped[str | None] = mapped_column(String(500), nullable=True)
    evidence: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[StudyTaskStatus] = mapped_column(
        SqlEnum(
            StudyTaskStatus,
            native_enum=False,
            values_callable=lambda statuses: [status.value for status in statuses],
        ),
        nullable=False,
        default=StudyTaskStatus.TODO,
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
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
    study_plan: Mapped["StudyPlan"] = relationship(back_populates="tasks")
