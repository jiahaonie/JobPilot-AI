"""Persistence operations for jobs."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job import Job


class JobRepository:
    """Encapsulate SQLAlchemy queries for the job aggregate."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, job: Job) -> Job:
        """Stage a new job and populate database-generated fields."""

        self.session.add(job)
        self.session.flush()
        return job

    def get(self, job_id: int) -> Job | None:
        """Find a job by its primary key."""

        return self.session.get(Job, job_id)

    def list(self, *, offset: int = 0, limit: int = 100) -> list[Job]:
        """Return jobs ordered from newest to oldest."""

        statement = (
            select(Job)
            .order_by(Job.created_at.desc(), Job.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def delete(self, job: Job) -> None:
        """Stage a job deletion."""

        self.session.delete(job)
