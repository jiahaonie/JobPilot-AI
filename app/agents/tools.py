"""工具输入契约与注册元数据。"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from pydantic import BaseModel, Field, field_validator


class GetJobRequirementsInput(BaseModel):
    """读取单个岗位结构化要求的输入。"""

    job_id: int = Field(ge=1)


class CompareResumeWithJobInput(BaseModel):
    """简历与岗位比较工具的输入。"""

    job_id: int = Field(ge=1)
    resume_id: int = Field(ge=1)


class SearchLearningMaterialInput(BaseModel):
    """知识库搜索输入。"""

    query: str = Field(min_length=1, max_length=2_000)
    top_k: int = Field(default=5, ge=1, le=20)
    max_distance: float | None = Field(default=None, ge=0.0, le=2.0)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        """去除查询首尾空白，并拒绝空查询。"""
        normalized = value.strip()
        if not normalized:
            raise ValueError("query cannot be blank")
        return normalized


class CreateStudyPlanInput(BaseModel):
    """基于一份不可变匹配报告创建学习计划。"""

    match_report_id: int = Field(ge=1)
    deadline: date | None = None


class UpdateApplicationStatusInput(BaseModel):
    """显式更新投递状态的输入。"""

    job_id: int = Field(ge=1)
    status: str


@dataclass(frozen=True)
class ToolSpec:
    """提供给编排器的已校验工具契约。"""

    name: str
    description: str
    input_model: type[BaseModel]
    handler: Callable[[Any], Any]
