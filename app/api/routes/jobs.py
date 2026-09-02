"""岗位 HTTP 端点。"""

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel

from app.api.dependencies import (
    get_job_analysis_service,
    get_job_requirement_service,
    get_job_service,
    get_match_report_service,
    get_match_service,
)
from app.schemas.job import JobCreate, JobRead, JobUpdate
from app.schemas.match_report import MatchReportRead
from app.schemas.matching import MatchReport
from app.schemas.requirements import JobRequirement
from app.services.analysis import JobAnalysisService
from app.services.job import JobService
from app.services.match_report import MatchReportService
from app.services.matching import MatchService
from app.services.requirements import JobRequirementService

router = APIRouter(prefix="/jobs", tags=["jobs"])


class MatchRequest(BaseModel):
    """选择与当前岗位匹配的简历。"""

    resume_id: int


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
def create_job(
    payload: JobCreate,
    service: JobService = Depends(get_job_service),
) -> JobRead:
    """创建并保存岗位描述。"""
    return service.create(payload)


@router.get("", response_model=list[JobRead])
def list_jobs(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    service: JobService = Depends(get_job_service),
) -> list[JobRead]:
    """通过受限分页列出已保存岗位。"""
    return service.list(offset=offset, limit=limit)


@router.get("/{job_id}", response_model=JobRead)
def get_job(
    job_id: int,
    service: JobService = Depends(get_job_service),
) -> JobRead:
    """返回一个已保存岗位。"""
    return service.get(job_id)


@router.patch("/{job_id}", response_model=JobRead)
def update_job(
    job_id: int,
    payload: JobUpdate,
    service: JobService = Depends(get_job_service),
) -> JobRead:
    """对一个已保存岗位执行部分更新。"""
    return service.update(job_id, payload)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: int,
    service: JobService = Depends(get_job_service),
) -> None:
    """删除一个已保存岗位。"""
    service.delete(job_id)


@router.post("/{job_id}/analyze", response_model=JobRequirement)
def analyze_job(
    job_id: int,
    service: JobAnalysisService = Depends(get_job_analysis_service),
) -> JobRequirement:
    """显式分析已保存 JD，并覆盖最新岗位要求。"""
    return service.analyze_job(job_id)


@router.get("/{job_id}/requirements", response_model=JobRequirement)
def get_job_requirements(
    job_id: int,
    service: JobRequirementService = Depends(get_job_requirement_service),
) -> JobRequirement:
    """读取已保存要求，不调用 LLM，也不写入数据。"""
    return service.get(job_id)


@router.post("/{job_id}/match", response_model=MatchReport)
def match_job_with_resume(
    job_id: int,
    payload: MatchRequest,
    service: MatchService = Depends(get_match_service),
) -> MatchReport:
    """将已保存简历与岗位结构化要求比较。"""
    return service.match(job_id=job_id, resume_id=payload.resume_id)


@router.post(
    "/{job_id}/match-reports",
    response_model=MatchReportRead,
    status_code=status.HTTP_201_CREATED,
)
def create_match_report(
    job_id: int,
    payload: MatchRequest,
    service: MatchReportService = Depends(get_match_report_service),
) -> MatchReportRead:
    """计算并保存不可变的简历岗位匹配报告。"""
    return service.create(job_id=job_id, resume_id=payload.resume_id)
