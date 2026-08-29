"""Job application service."""

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundError
from app.models.job import Job
from app.repositories.job import JobRepository
from app.schemas.job import JobCreate, JobUpdate


class JobService:
    """Coordinate job use cases and keep transaction ownership out of routes."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = JobRepository(session)

    def create(self, payload: JobCreate) -> Job:
        """Save a job description."""

        job = Job(**payload.model_dump())
        self.repository.add(job)
        self.session.commit()
        self.session.refresh(job)
        return job

    def get(self, job_id: int) -> Job:
        """Return a job or raise a domain-level not-found error."""

        job = self.repository.get(job_id)
        if job is None:
            raise ResourceNotFoundError(f"Job {job_id} was not found")
        return job

    def list(self, *, offset: int = 0, limit: int = 100) -> list[Job]:
        """Return a bounded list of saved jobs."""

        return self.repository.list(offset=offset, limit=limit)

    def update(self, job_id: int, payload: JobUpdate) -> Job:
        """Apply a partial update and return the refreshed job."""

        job = self.get(job_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(job, field, value)
        self.session.commit()
        self.session.refresh(job)
        return job

    def delete(self, job_id: int) -> None:
        """Delete a saved job."""

        job = self.get(job_id)
        self.repository.delete(job)
        self.session.commit()
