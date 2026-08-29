"""Job request and response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import JobStatus


class JobFields(BaseModel):
    """Fields shared by job creation and the read model."""

    company_name: str = Field(min_length=1, max_length=200)
    job_title: str = Field(min_length=1, max_length=200)
    city: str | None = Field(default=None, max_length=100)
    internship_duration: str | None = Field(default=None, max_length=100)
    raw_text: str = Field(min_length=1)
    source_url: str | None = Field(default=None, max_length=1_000)


class JobCreate(JobFields):
    """Payload for saving a job description."""

    status: JobStatus = JobStatus.PENDING_ANALYSIS


class JobUpdate(BaseModel):
    """Partial update payload for user-managed job fields."""

    company_name: str | None = Field(default=None, min_length=1, max_length=200)
    job_title: str | None = Field(default=None, min_length=1, max_length=200)
    city: str | None = Field(default=None, max_length=100)
    internship_duration: str | None = Field(default=None, max_length=100)
    raw_text: str | None = Field(default=None, min_length=1)
    source_url: str | None = Field(default=None, max_length=1_000)
    status: JobStatus | None = None


class JobRead(JobFields):
    """Payload returned for a saved job."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    status: JobStatus
    created_at: datetime
    updated_at: datetime
