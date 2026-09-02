"""简历存储、上传与分析 HTTP 端点。"""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status

from app.api.dependencies import (
    get_resume_analysis_service,
    get_resume_file_service,
    get_resume_service,
)
from app.core.config import Settings, get_settings
from app.schemas.resume import ResumeCreate, ResumeRead, ResumeSummary
from app.services.resume import ResumeAnalysisService, ResumeService
from app.services.resume_file import ResumeFileService

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("", response_model=ResumeRead, status_code=status.HTTP_201_CREATED)
def create_resume(
    payload: ResumeCreate,
    service: ResumeService = Depends(get_resume_service),
) -> ResumeRead:
    """保存简历文本，不调用 LLM。"""
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
    """提取并保存上传简历，不调用 LLM。"""
    content = file.file.read(settings.resume_max_upload_bytes + 1)
    parsed = file_service.parse(filename=file.filename, content=content)
    return service.create(
        ResumeCreate(
            title=title or Path(parsed.source_name).stem,
            raw_text=parsed.raw_text,
        )
    )


@router.get("", response_model=list[ResumeSummary])
def list_resumes(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    service: ResumeService = Depends(get_resume_service),
) -> list[ResumeSummary]:
    """分页返回不含简历原文的摘要。"""
    return service.list_all(offset=offset, limit=limit)


@router.get("/{resume_id}", response_model=ResumeRead)
def get_resume(
    resume_id: int,
    service: ResumeService = Depends(get_resume_service),
) -> ResumeRead:
    """返回一份已保存简历及其分析生命周期状态。"""
    return service.get(resume_id)


@router.post("/{resume_id}/analyze", response_model=ResumeRead)
def analyze_resume(
    resume_id: int,
    service: ResumeAnalysisService = Depends(get_resume_analysis_service),
) -> ResumeRead:
    """对一份已保存简历运行或重试 LLM 技能提取。"""
    return service.analyze(resume_id)


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(
    resume_id: int,
    service: ResumeService = Depends(get_resume_service),
) -> None:
    """删除一份已保存简历。"""
    service.delete(resume_id)
