"""基于 Pydantic 的 API 与领域模型。"""

from app.schemas.job import JobCreate, JobRead, JobResumeBind, JobStatusUpdate, JobUpdate
from app.schemas.requirements import JobRequirement
from app.schemas.study_plan import (
    StudyPlanCreate,
    StudyPlanRead,
    StudyTaskRead,
    StudyTaskUpdate,
)

__all__ = [
    "JobCreate",
    "JobRead",
    "JobRequirement",
    "JobResumeBind",
    "JobStatusUpdate",
    "JobUpdate",
    "StudyPlanCreate",
    "StudyPlanRead",
    "StudyTaskRead",
    "StudyTaskUpdate",
]
