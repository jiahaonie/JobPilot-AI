"""Job HTTP endpoints."""

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel

from app.api.dependencies import (
    get_job_analysis_service,
    get_job_requirement_service,
    get_job_service,
    get_match_service,
)
from app.schemas.job import JobCreate, JobRead, JobUpdate
from app.schemas.matching import MatchReport
from app.schemas.requirements import JobRequirement
from app.services.analysis import JobAnalysisService
from app.services.job import JobService
from app.services.matching import MatchService
from app.services.requirements import JobRequirementService

router = APIRouter(prefix="/jobs", tags=["jobs"])


class MatchRequest(BaseModel):
    """Selects the resume to match against this job."""

    resume_id: int


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
def create_job(
    payload: JobCreate,
    service: JobService = Depends(get_job_service),
) -> JobRead:
    """Create and persist a job description."""

    return service.create(payload)


@router.get("", response_model=list[JobRead])
def list_jobs(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    service: JobService = Depends(get_job_service),
) -> list[JobRead]:
    """List saved jobs with bounded pagination."""

    return service.list(offset=offset, limit=limit)


@router.get("/{job_id}", response_model=JobRead)
def get_job(
    job_id: int,
    service: JobService = Depends(get_job_service),
) -> JobRead:
    """Return one saved job."""

    return service.get(job_id)


@router.patch("/{job_id}", response_model=JobRead)
def update_job(
    job_id: int,
    payload: JobUpdate,
    service: JobService = Depends(get_job_service),
) -> JobRead:
    """Apply a partial update to one saved job."""

    return service.update(job_id, payload)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: int,
    service: JobService = Depends(get_job_service),
) -> None:
    """Delete one saved job."""

    service.delete(job_id)


@router.post("/{job_id}/analyze", response_model=JobRequirement)
def analyze_job(
    job_id: int,
    service: JobAnalysisService = Depends(get_job_analysis_service),
) -> JobRequirement:
    """Explicitly analyze a saved JD and overwrite its latest requirements."""

    return service.analyze_job(job_id)


@router.get("/{job_id}/requirements", response_model=JobRequirement)
def get_job_requirements(
    job_id: int,
    service: JobRequirementService = Depends(get_job_requirement_service),
) -> JobRequirement:
    """Read stored requirements without invoking an LLM or writing data."""

    return service.get(job_id)


@router.post("/{job_id}/match", response_model=MatchReport)
def match_job_with_resume(
    job_id: int,
    payload: MatchRequest,
    service: MatchService = Depends(get_match_service),
) -> MatchReport:
    """Compare a saved resume against this job's structured requirements."""

    return service.match(job_id=job_id, resume_id=payload.resume_id)
