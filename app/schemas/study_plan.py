"""学习计划和任务的 API 数据契约。"""

from datetime import UTC, date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.models.enums import StudyPlanStatus, StudyTaskPhase, StudyTaskStatus


class StudyPlanCreate(BaseModel):
    """基于一份不可变匹配报告创建学习计划。"""

    model_config = ConfigDict(extra="forbid")

    match_report_id: int = Field(ge=1)
    deadline: date | None = None


class StudyTaskUpdate(BaseModel):
    """第一版只允许用户更新任务状态。"""

    model_config = ConfigDict(extra="forbid")

    status: StudyTaskStatus


class StudyTaskRead(BaseModel):
    """返回一项规则生成的学习任务。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    study_plan_id: int
    skill: str
    phase: StudyTaskPhase
    title: str
    completion_criteria: str
    resource_query: str
    position: int
    status: StudyTaskStatus
    due_date: date | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @field_serializer("completed_at", "created_at", "updated_at", when_used="json")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        """将 SQLite 返回的无时区时间统一解释为 UTC。"""
        if value is None:
            return None
        normalized = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        return normalized.astimezone(UTC).isoformat().replace("+00:00", "Z")


class StudyPlanRead(BaseModel):
    """返回计划、动态进度和按顺序排列的任务。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    match_report_id: int
    deadline: date | None
    generation_method: str
    status: StudyPlanStatus
    completed_count: int
    task_count: int
    tasks: list[StudyTaskRead]
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at", when_used="json")
    def serialize_datetime(self, value: datetime) -> str:
        """将 SQLite 返回的无时区时间统一解释为 UTC。"""
        normalized = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        return normalized.astimezone(UTC).isoformat().replace("+00:00", "Z")
