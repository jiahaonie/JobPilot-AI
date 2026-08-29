"""Resume-to-job matching contracts."""

from pydantic import BaseModel, Field


class SkillGap(BaseModel):
    """One required skill and the job text that supports it."""

    skill: str
    evidence: str


class MatchReport(BaseModel):
    """Explained skill comparison between a resume and one job."""

    matched_skills: list[str] = Field(default_factory=list)
    bonus_skills: list[str] = Field(default_factory=list)
    missing_skills: list[SkillGap] = Field(default_factory=list)
    priority_skills: list[SkillGap] = Field(default_factory=list)
