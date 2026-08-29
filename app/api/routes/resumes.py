"""Resume HTTP endpoints."""

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_resume_service
from app.schemas.resume import ResumeCreate, ResumeRead
from app.services.resume import ResumeService

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("", response_model=ResumeRead, status_code=status.HTTP_201_CREATED)
def create_resume(
    payload: ResumeCreate,
    service: ResumeService = Depends(get_resume_service),
) -> ResumeRead:
    """Save a resume and extract its skills via the LLM."""

    return service.create(payload)


@router.get("", response_model=list[ResumeRead])
def list_resumes(
    service: ResumeService = Depends(get_resume_service),
) -> list[ResumeRead]:
    """List all saved resumes."""

    return service.list_all()


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(
    resume_id: int,
    service: ResumeService = Depends(get_resume_service),
) -> None:
    """Delete one saved resume."""

    service.delete(resume_id)
