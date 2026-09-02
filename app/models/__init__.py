"""基于 SQLAlchemy 的持久化模型。"""

from app.models.base import Base
from app.models.enums import (
    DocumentStatus,
    JobAnalysisStatus,
    JobStatus,
    ResumeAnalysisStatus,
    StudyPlanStatus,
    StudyTaskPhase,
    StudyTaskStatus,
)
from app.models.job import Job
from app.models.job_analysis import JobAnalysis
from app.models.job_requirement import JobRequirementRow
from app.models.job_resume import JobResume
from app.models.knowledge_document import KnowledgeDocument
from app.models.match_report import MatchReportRow
from app.models.resume import Resume
from app.models.resume_analysis import ResumeAnalysis
from app.models.study_plan import StudyPlan
from app.models.study_task import StudyTask

__all__ = [
    "Base",
    "DocumentStatus",
    "Job",
    "JobAnalysis",
    "JobAnalysisStatus",
    "JobRequirementRow",
    "JobResume",
    "JobStatus",
    "KnowledgeDocument",
    "MatchReportRow",
    "Resume",
    "ResumeAnalysis",
    "ResumeAnalysisStatus",
    "StudyPlan",
    "StudyPlanStatus",
    "StudyTask",
    "StudyTaskPhase",
    "StudyTaskStatus",
]
