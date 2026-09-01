"""Persisted match-report response contracts."""

from datetime import datetime

from pydantic import ConfigDict

from app.schemas.matching import MatchReport


class MatchReportRead(MatchReport):
    """One stored matching snapshot with source and scoring metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    resume_id: int
    required_skills_snapshot: list[str]
    preferred_skills_snapshot: list[str]
    resume_skills_snapshot: list[str]
    job_requirement_updated_at: datetime
    resume_analyzed_at: datetime | None
    scoring_version: str
    created_at: datetime
