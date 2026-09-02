"""岗位请求与响应模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import JobAnalysisStatus, JobStatus

MAX_JOB_TEXT_CHARS = 100_000


class JobFields(BaseModel):
    """岗位创建与读取模型共用字段。"""

    model_config = ConfigDict(extra="forbid")

    company_name: str = Field(min_length=1, max_length=200)
    job_title: str = Field(min_length=1, max_length=200)
    city: str | None = Field(default=None, max_length=100)
    internship_duration: str | None = Field(default=None, max_length=100)
    raw_text: str = Field(min_length=1, max_length=MAX_JOB_TEXT_CHARS)
    source_url: str | None = Field(default=None, max_length=1_000)

    @field_validator("company_name", "job_title", "city", "internship_duration", "raw_text")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        """去除首尾空白，并拒绝只有空白的文本。"""
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("text cannot be blank")
        return normalized


class JobCreate(JobFields):
    """保存岗位描述的载荷。"""


class JobUpdate(BaseModel):
    """用户可管理岗位字段的部分更新载荷。"""

    model_config = ConfigDict(extra="forbid")

    company_name: str | None = Field(default=None, min_length=1, max_length=200)
    job_title: str | None = Field(default=None, min_length=1, max_length=200)
    city: str | None = Field(default=None, max_length=100)
    internship_duration: str | None = Field(default=None, max_length=100)
    raw_text: str | None = Field(default=None, min_length=1, max_length=MAX_JOB_TEXT_CHARS)
    source_url: str | None = Field(default=None, max_length=1_000)

    @field_validator("company_name", "job_title", "city", "internship_duration", "raw_text")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        """去除首尾空白，并拒绝只有空白的已提供文本。"""
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("text cannot be blank")
        return normalized


class JobRead(JobFields):
    """返回已保存岗位的载荷。"""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: int
    status: JobStatus | None
    resume_id: int | None
    analysis_status: JobAnalysisStatus
    analysis_error: str | None
    analyzed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class JobResumeBind(BaseModel):
    """为岗位选择第一版唯一投递简历的请求。"""

    model_config = ConfigDict(extra="forbid")

    resume_id: int = Field(ge=1)


class JobStatusUpdate(BaseModel):
    """按照受控状态机推进岗位投递阶段的请求。"""

    model_config = ConfigDict(extra="forbid")

    status: JobStatus
