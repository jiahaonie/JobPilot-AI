"""Persistence operations for structured job requirements."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job_requirement import JobRequirementRow


class JobRequirementRepository:
    """Encapsulate SQLAlchemy queries for the job-requirements aggregate."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_job(self, job_id: int) -> JobRequirementRow | None:
        """Return the latest structured analysis for one job, if any."""

        statement = select(JobRequirementRow).where(
            JobRequirementRow.job_id == job_id
        )
        return self.session.scalar(statement)

    def upsert(self, row: JobRequirementRow) -> JobRequirementRow:
        """Stage the row for commit, updating in place when one already exists."""

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
