"""只读访问已持久化的岗位要求。"""

from sqlalchemy.orm import Session

from app.core.exceptions import JobRequirementNotFoundError
from app.repositories.job_requirement import JobRequirementRepository
from app.schemas.requirements import JobRequirement


class JobRequirementService:
    """返回已保存的 JD 分析，不调用 LLM，也不写入数据。"""

    def __init__(self, session: Session) -> None:
        self.repository = JobRequirementRepository(session)

    def get(self, job_id: int) -> JobRequirement:
        """返回最新岗位要求；不存在时给出明确异常。"""
        row = self.repository.get_by_job(job_id)
        if row is None:
            raise JobRequirementNotFoundError(f"Job {job_id} has not been analyzed yet")
        return JobRequirement(
            job_title=row.job_title,
            required_skills=row.required_skills,
            preferred_skills=row.preferred_skills,
            education=row.education,
            internship_duration=row.internship_duration,
            responsibilities=row.responsibilities,
            evidence=row.evidence,
        )
