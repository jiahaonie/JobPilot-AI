"""岗位请求与响应模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import JobStatus

MAX_JOB_TEXT_CHARS = 100_000


class JobFields(BaseModel):
    """岗位创建与读取模型共用字段。"""

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

    status: JobStatus = JobStatus.PENDING_ANALYSIS


class JobUpdate(BaseModel):
    """用户可管理岗位字段的部分更新载荷。"""

    company_name: str | None = Field(default=None, min_length=1, max_length=200)
    job_title: str | None = Field(default=None, min_length=1, max_length=200)
    city: str | None = Field(default=None, max_length=100)
    internship_duration: str | None = Field(default=None, max_length=100)
    raw_text: str | None = Field(default=None, min_length=1, max_length=MAX_JOB_TEXT_CHARS)
    source_url: str | None = Field(default=None, max_length=1_000)
    status: JobStatus | None = None

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

    model_config = ConfigDict(from_attributes=True)

    id: int
    status: JobStatus
    created_at: datetime
    updated_at: datetime
