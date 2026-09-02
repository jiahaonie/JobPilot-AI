"""供 LLM 阶段使用的结构化岗位要求契约。"""

from pydantic import BaseModel, Field


class JobRequirement(BaseModel):
    """从不可信岗位描述中提取并经 LLM 校验的结构。"""

    job_title: str = Field(min_length=1)
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    education: str | None = None
    internship_duration: str | None = None
    responsibilities: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(
        default_factory=list,
        description="Original text snippets supporting each extracted requirement.",
    )
