"""Tool input contracts and registration metadata."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel


class GetJobRequirementsInput(BaseModel):
    """Input for reading structured requirements for one job."""

    job_id: int


class CompareResumeWithJobInput(BaseModel):
    """Input for a future resume-to-job comparison tool."""

    job_id: int
    resume_id: int


class SearchLearningMaterialInput(BaseModel):
    """Input for knowledge-base search."""

    query: str
    top_k: int = 5
    max_distance: float | None = None


class CreateStudyPlanInput(BaseModel):
    """Input for study-plan generation."""

    job_id: int
    deadline: str | None = None


class UpdateApplicationStatusInput(BaseModel):
    """Input for an explicit application-status update."""

    job_id: int
    status: str


@dataclass(frozen=True)
class ToolSpec:
    """A validated tool contract supplied to the orchestrator."""

    name: str
    description: str
    input_model: type[BaseModel]
    handler: Callable[[Any], Any]
