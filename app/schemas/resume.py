"""简历请求与响应契约。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ResumeAnalysisStatus

MAX_RESUME_TEXT_CHARS = 100_000


class ResumeSkill(BaseModel):
    """由 LLM 提取并通过校验的技能列表。"""

    skills: list[str] = Field(default_factory=list)


class ResumeCreate(BaseModel):
    """技能提取前用于保存简历的载荷。"""

    title: str | None = Field(default=None, max_length=200)
    raw_text: str = Field(min_length=1, max_length=MAX_RESUME_TEXT_CHARS)

    @field_validator("title", "raw_text")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        """去除首尾空白，并拒绝只有空白的文本。"""
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("text cannot be blank")
        return normalized


class ResumeRead(BaseModel):
    """返回单份已保存简历的载荷。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    raw_text: str
    skills: list[str]
    analysis_status: ResumeAnalysisStatus
    analysis_error: str | None
    analyzed_at: datetime | None
    created_at: datetime


class ResumeSummary(BaseModel):
    """列表接口返回的不含简历原文的摘要。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    skills: list[str]
    analysis_status: ResumeAnalysisStatus
    analysis_error: str | None
    analyzed_at: datetime | None
    created_at: datetime
