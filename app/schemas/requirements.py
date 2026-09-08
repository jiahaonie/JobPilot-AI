"""供 LLM 阶段使用的结构化岗位要求契约。"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SkillRequirement(BaseModel):
    """一组能够以确定性规则比较的原子技能要求。"""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=200)
    importance: Literal["required", "preferred"]
    match_mode: Literal["any", "all"]
    options: list[str] = Field(min_length=1)
    evidence: str = Field(min_length=1)

    @field_validator("label", "evidence")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("options")
    @classmethod
    def strip_options(cls, options: list[str]) -> list[str]:
        stripped = [option.strip() for option in options]
        if any(not option for option in stripped):
            raise ValueError("skill options cannot be blank")
        return stripped


class UnscoredRequirement(BaseModel):
    """不能仅凭技能词可靠评分的岗位要求。"""

    model_config = ConfigDict(extra="forbid")

    category: Literal["experience", "education", "soft_skill", "other"]
    text: str = Field(min_length=1)
    evidence: str = Field(min_length=1)

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, value: object) -> str:
        """未知的非评分分类安全归入 other，不影响技能评分主链路。"""
        allowed = {"experience", "education", "soft_skill", "other"}
        return value if isinstance(value, str) and value in allowed else "other"


class JobRequirement(BaseModel):
    """从不可信岗位描述中提取并经 LLM 校验的结构。"""

    job_title: str = Field(min_length=1)
    extraction_version: str = "job-requirements-v2"
    skill_requirements: list[SkillRequirement] = Field(default_factory=list)
    unscored_requirements: list[UnscoredRequirement] = Field(default_factory=list)
    # V1 兼容字段由应用从 skill_requirements 推导，不参与 V2 匹配决策。
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    education: str | None = None
    internship_duration: str | None = None
    responsibilities: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(
        default_factory=list,
        description="Original text snippets supporting each extracted requirement.",
    )
