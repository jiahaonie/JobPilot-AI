"""学习计划和任务的 API 数据契约。"""

from datetime import UTC, date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator

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
    learning_content: str | None
    action: str | None
    completion_criteria: str
    resource_query: str | None
    evidence: list["StudyTaskEvidence"] | None
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
    coverage: "StudyPlanCoverage | None"
    generation_metadata: dict | None
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


class StudyTaskEvidence(BaseModel):
    """生成时冻结的一条资料依据。"""

    chunk_id: str
    document_id: int
    source_name: str
    excerpt: str
    location: str | None = None


class UncoveredSkill(BaseModel):
    """没有生成任务的技能及其稳定原因。"""

    skill: str
    reason_code: str


class StudyPlanCoverage(BaseModel):
    """计划生成时的技能覆盖快照。"""

    target_skills: list[str]
    covered_skills: list[str]
    uncovered_skills: list[UncoveredSkill]


class GeneratedStudyTask(BaseModel):
    """模型生成、尚未绑定可信原文的任务候选。"""

    phase: StudyTaskPhase
    title: str = Field(min_length=1, max_length=500)
    learning_content: str = Field(min_length=1, max_length=4_000)
    action: str = Field(min_length=1, max_length=4_000)
    completion_criteria: str = Field(min_length=1, max_length=4_000)
    evidence_ids: list[str] = Field(min_length=1, max_length=5)


class GeneratedSkillPlan(BaseModel):
    """一个目标技能的生成结果。"""

    skill: str = Field(min_length=1, max_length=200)
    support_status: Literal["supported", "insufficient_support"]
    tasks: list[GeneratedStudyTask] = Field(max_length=12)
    reason: str | None = Field(default=None, max_length=1_000)

    @model_validator(mode="after")
    def validate_support(self) -> "GeneratedSkillPlan":
        if self.support_status == "supported" and not self.tasks:
            raise ValueError("supported skills require at least one task")
        if self.support_status == "insufficient_support" and self.tasks:
            raise ValueError("insufficient skills cannot include tasks")
        return self


class GeneratedStudyPlan(BaseModel):
    """学习任务生成客户端的完整结构化输出。"""

    skills: list[GeneratedSkillPlan] = Field(min_length=1)
