"""Resume request and response contracts."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ResumeSkill(BaseModel):
    """LLM-validated skill list extracted from a resume."""

    skills: list[str] = Field(default_factory=list)


class ResumeCreate(BaseModel):
    """Payload for saving a resume before skill extraction."""

    title: str | None = Field(default=None, max_length=200)
    raw_text: str = Field(min_length=1)


class ResumeRead(BaseModel):
    """Payload returned for a saved resume."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    raw_text: str
    skills: list[str]
    created_at: datetime
