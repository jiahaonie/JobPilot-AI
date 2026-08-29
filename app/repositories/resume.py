"""Persistence operations for resumes."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.resume import Resume


class ResumeRepository:
    """Encapsulate SQLAlchemy queries for the resume aggregate."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, resume: Resume) -> Resume:
        """Stage a new resume and populate database-generated fields."""

        self.session.add(resume)
        self.session.flush()
        return resume

    def get(self, resume_id: int) -> Resume | None:
        """Find a resume by its primary key."""

        return self.session.get(Resume, resume_id)

    def list(self) -> list[Resume]:
        """Return all resumes ordered from newest to oldest."""

        statement = select(Resume).order_by(Resume.created_at.desc(), Resume.id.desc())
        return list(self.session.scalars(statement))

    def delete(self, resume: Resume) -> None:
        """Stage a resume deletion."""

        self.session.delete(resume)
