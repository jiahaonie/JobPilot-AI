"""读取已保存的简历岗位匹配报告。"""

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_match_report_service
from app.schemas.match_report import MatchReportRead
from app.services.match_report import MatchReportService

router = APIRouter(prefix="/match-reports", tags=["match-reports"])


@router.get("", response_model=list[MatchReportRead])
def list_match_reports(
    job_id: int | None = Query(default=None, ge=1),
    resume_id: int | None = Query(default=None, ge=1),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    service: MatchReportService = Depends(get_match_report_service),
) -> list[MatchReportRead]:
    """按可选岗位和简历条件列出历史报告。"""
    return service.list(
        job_id=job_id,
        resume_id=resume_id,
        offset=offset,
        limit=limit,
    )


@router.get("/{report_id}", response_model=MatchReportRead)
def get_match_report(
    report_id: int,
    service: MatchReportService = Depends(get_match_report_service),
) -> MatchReportRead:
    """返回一份不可变的历史匹配报告。"""
    return service.get(report_id)
