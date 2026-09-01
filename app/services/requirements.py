"""Read-only access to persisted job requirements."""

from sqlalchemy.orm import Session

from app.core.exceptions import JobRequirementNotFoundError
from app.repositories.job_requirement import JobRequirementRepository
from app.schemas.requirements import JobRequirement


class JobRequirementService:
    """Return stored JD analysis without invoking an LLM or writing data."""

    def __init__(self, session: Session) -> None:
        self.repository = JobRequirementRepository(session)

    def get(self, job_id: int) -> JobRequirement:
        """Return the latest persisted requirements or a clear not-found error."""

        row = self.repository.get_by_job(job_id)
        if row is None:
            raise JobRequirementNotFoundError(
                f"Job {job_id} has not been analyzed yet"
            )
        return JobRequirement(
            job_title=row.job_title,
            required_skills=row.required_skills,
            preferred_skills=row.preferred_skills,
            education=row.education,
            internship_duration=row.internship_duration,
            responsibilities=row.responsibilities,
            evidence=row.evidence,
        )
