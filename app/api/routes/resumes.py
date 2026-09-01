"""Resume storage, upload, and analysis HTTP endpoints."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from app.api.dependencies import (
    get_resume_analysis_service,
    get_resume_file_service,
    get_resume_service,
)
from app.core.config import Settings, get_settings
from app.schemas.resume import ResumeCreate, ResumeRead
from app.services.resume import ResumeAnalysisService, ResumeService
from app.services.resume_file import ResumeFileService

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("", response_model=ResumeRead, status_code=status.HTTP_201_CREATED)
def create_resume(
    payload: ResumeCreate,
    service: ResumeService = Depends(get_resume_service),
) -> ResumeRead:
    """Save resume text without invoking an LLM."""

    return service.create(payload)


@router.post(
    "/upload",
    response_model=ResumeRead,
    status_code=status.HTTP_201_CREATED,
)
def upload_resume(
    file: Annotated[
        UploadFile,
        File(description="UTF-8 TXT/Markdown or electronic PDF resume"),
    ],
    title: Annotated[str | None, Form(max_length=200)] = None,
    service: ResumeService = Depends(get_resume_service),
    file_service: ResumeFileService = Depends(get_resume_file_service),
    settings: Settings = Depends(get_settings),
) -> ResumeRead:
    """Extract and save an uploaded resume without invoking an LLM."""

    content = file.file.read(settings.resume_max_upload_bytes + 1)
    parsed = file_service.parse(filename=file.filename, content=content)
    return service.create(
        ResumeCreate(
            title=title or Path(parsed.source_name).stem,
            raw_text=parsed.raw_text,
        )
    )


@router.get("", response_model=list[ResumeRead])
def list_resumes(
    service: ResumeService = Depends(get_resume_service),
) -> list[ResumeRead]:
    """List all saved resumes."""

    return service.list_all()


@router.get("/{resume_id}", response_model=ResumeRead)
def get_resume(
    resume_id: int,
    service: ResumeService = Depends(get_resume_service),
) -> ResumeRead:
    """Return one saved resume with its analysis lifecycle state."""

    return service.get(resume_id)


@router.post("/{resume_id}/analyze", response_model=ResumeRead)
def analyze_resume(
    resume_id: int,
    service: ResumeAnalysisService = Depends(get_resume_analysis_service),
) -> ResumeRead:
    """Run or retry LLM skill extraction for one saved resume."""

    return service.analyze(resume_id)


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(
    resume_id: int,
    service: ResumeService = Depends(get_resume_service),
) -> None:
    """Delete one saved resume."""

    service.delete(resume_id)
