"""Structured job-requirement contract for the future LLM phase."""

from pydantic import BaseModel, Field


class JobRequirement(BaseModel):
    """LLM-validated structure extracted from an untrusted job description."""

    job_title: str = Field(min_length=1)
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    education: str | None = None
    internship_duration: str | None = None
    responsibilities: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(
        default_factory=list,
        description="Original text snippets supporting each extracted requirement.",
    )
