"""学习计划创建、查询和任务状态更新端点。"""

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import (
    get_builtin_knowledge_search_service,
    get_llm_client,
    get_runtime_settings,
    get_study_plan_service,
)
from app.core.config import Settings, parse_builtin_document_ids
from app.llm.client import StructuredLLMClient
from app.schemas.study_plan import (
    StudyPlanCreate,
    StudyPlanRead,
    StudyTaskRead,
    StudyTaskUpdate,
)
from app.services.search import KnowledgeSearchService
from app.services.study_plan import StudyPlanService

router = APIRouter(prefix="/study-plans", tags=["study-plans"])
task_router = APIRouter(prefix="/study-tasks", tags=["study-plans"])


@router.post("", response_model=StudyPlanRead, status_code=status.HTTP_201_CREATED)
def create_study_plan(
    payload: StudyPlanCreate,
    response: Response,
    service: StudyPlanService = Depends(get_study_plan_service),
    search_service: KnowledgeSearchService = Depends(get_builtin_knowledge_search_service),
    client: StructuredLLMClient = Depends(get_llm_client),
    settings: Settings = Depends(get_runtime_settings),
) -> StudyPlanRead:
    """基于一份不可变匹配报告创建或返回有依据的学习计划。"""
    result = service.create_rag(
        match_report_id=payload.match_report_id,
        deadline=payload.deadline,
        search_service=search_service,
        client=client,
        builtin_document_ids=parse_builtin_document_ids(settings.rag_builtin_document_ids),
        model_name=settings.llm_model,
        prompt_version=settings.rag_plan_prompt_version,
        top_k=settings.rag_plan_top_k,
        context_char_limit=settings.rag_plan_context_chars,
        time_budget_seconds=settings.rag_plan_time_budget_seconds,
    )
    response.status_code = status.HTTP_201_CREATED if result.created else status.HTTP_200_OK
    return result.plan


@router.get("", response_model=list[StudyPlanRead])
def list_study_plans(
    match_report_id: int | None = Query(default=None, ge=1),
    job_id: int | None = Query(default=None, ge=1),
    resume_id: int | None = Query(default=None, ge=1),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    service: StudyPlanService = Depends(get_study_plan_service),
) -> list[StudyPlanRead]:
    """按可选岗位和简历筛选学习计划。"""
    return service.list_all(
        match_report_id=match_report_id,
        job_id=job_id,
        resume_id=resume_id,
        offset=offset,
        limit=limit,
    )


@router.get("/{plan_id}", response_model=StudyPlanRead)
def get_study_plan(
    plan_id: int,
    service: StudyPlanService = Depends(get_study_plan_service),
) -> StudyPlanRead:
    """返回一份学习计划及其有序任务。"""
    return service.get(plan_id)


@task_router.patch("/{task_id}", response_model=StudyTaskRead)
def update_study_task(
    task_id: int,
    payload: StudyTaskUpdate,
    service: StudyPlanService = Depends(get_study_plan_service),
) -> StudyTaskRead:
    """按照受控状态机更新学习任务状态。"""
    return service.update_task(task_id=task_id, target=payload.status)
