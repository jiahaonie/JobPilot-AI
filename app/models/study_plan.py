"""学习计划持久化模型。"""

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import StudyPlanStatus, StudyTaskStatus

if TYPE_CHECKING:
    from app.models.study_task import StudyTask


def utc_now() -> datetime:
    """返回供应用记录使用的带时区时间戳。"""
    return datetime.now(UTC)


class StudyPlan(Base):
    """绑定一份不可变匹配报告的规则学习计划。"""

    __tablename__ = "study_plans"
    __table_args__ = (
        UniqueConstraint(
            "match_report_id",
            name="uq_study_plans_match_report_id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    match_report_id: Mapped[int] = mapped_column(
        ForeignKey("match_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    generation_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="rule_v1",
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
    tasks: Mapped[list["StudyTask"]] = relationship(
        back_populates="study_plan",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="StudyTask.position",
    )

    @property
    def status(self) -> StudyPlanStatus:
        """根据任务状态计算计划状态，不重复持久化派生数据。"""
        if not self.tasks or all(task.status is StudyTaskStatus.TODO for task in self.tasks):
            return StudyPlanStatus.NOT_STARTED
        if all(task.status is StudyTaskStatus.DONE for task in self.tasks):
            return StudyPlanStatus.COMPLETED
        return StudyPlanStatus.IN_PROGRESS

    @property
    def task_count(self) -> int:
        """返回计划任务总数。"""
        return len(self.tasks)

    @property
    def completed_count(self) -> int:
        """返回已完成任务数量。"""
        return sum(task.status is StudyTaskStatus.DONE for task in self.tasks)
