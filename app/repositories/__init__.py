"""数据库访问对象。"""

from app.repositories.job import JobRepository
from app.repositories.job_resume import JobResumeRepository
from app.repositories.study_plan import StudyPlanRepository

__all__ = [
    "JobRepository",
    "JobResumeRepository",
    "StudyPlanRepository",
]
