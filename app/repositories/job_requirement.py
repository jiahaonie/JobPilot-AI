"""结构化岗位要求的持久化操作。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job_requirement import JobRequirementRow


class JobRequirementRepository:
    """封装岗位要求聚合的 SQLAlchemy 查询。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_job(self, job_id: int) -> JobRequirementRow | None:
        """返回一个岗位的最新结构化分析（若有）。"""
        statement = select(JobRequirementRow).where(JobRequirementRow.job_id == job_id)
        return self.session.scalar(statement)

    def upsert(self, row: JobRequirementRow) -> JobRequirementRow:
        """暂存待提交记录；已有记录时原位更新。"""
        existing = self.get_by_job(row.job_id)
        if existing is not None:
            existing.job_title = row.job_title
            existing.required_skills = row.required_skills
            existing.preferred_skills = row.preferred_skills
            existing.education = row.education
            existing.internship_duration = row.internship_duration
            existing.responsibilities = row.responsibilities
            existing.evidence = row.evidence
            return existing
        self.session.add(row)
        return row

    def delete_by_job(self, job_id: int) -> None:
        """删除岗位已有的结构化分析（若存在）。"""
        existing = self.get_by_job(job_id)
        if existing is not None:
            self.session.delete(existing)
