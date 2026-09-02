"""向模型选工具工作流开放的真实应用处理器。"""

from sqlalchemy.orm import Session

from app.agents.tools import (
    CompareResumeWithJobInput,
    CreateStudyPlanInput,
    GetJobRequirementsInput,
    SearchLearningMaterialInput,
    ToolSpec,
)
from app.core.exceptions import JobRequirementNotFoundError
from app.repositories.job_requirement import JobRequirementRepository
from app.schemas.requirements import JobRequirement
from app.schemas.study_plan import StudyPlanRead
from app.services.matching import MatchService
from app.services.search import KnowledgeSearchService
from app.services.study_plan import StudyPlanService


def build_real_tool_specs(
    *,
    session: Session,
    search_service: KnowledgeSearchService,
) -> tuple[ToolSpec, ...]:
    """将四个模型可见工具绑定到真实仓库和服务。"""
    requirement_repository = JobRequirementRepository(session)
    match_service = MatchService(session)
    study_plan_service = StudyPlanService(session)

    def get_job_requirements(arguments: GetJobRequirementsInput) -> dict:
        row = requirement_repository.get_by_job(arguments.job_id)
        if row is None:
            raise JobRequirementNotFoundError(f"Job {arguments.job_id} has not been analyzed yet")
        return JobRequirement(
            job_title=row.job_title,
            required_skills=row.required_skills,
            preferred_skills=row.preferred_skills,
            education=row.education,
            internship_duration=row.internship_duration,
            responsibilities=row.responsibilities,
            evidence=row.evidence,
        ).model_dump(mode="json")

    def compare_resume_with_job(arguments: CompareResumeWithJobInput) -> dict:
        return match_service.match(
            job_id=arguments.job_id,
            resume_id=arguments.resume_id,
        ).model_dump(mode="json")

    def search_learning_material(arguments: SearchLearningMaterialInput) -> dict:
        return search_service.search(
            query=arguments.query,
            top_k=arguments.top_k,
            max_distance=arguments.max_distance,
        ).model_dump(mode="json")

    def create_study_plan(arguments: CreateStudyPlanInput) -> dict:
        plan = study_plan_service.create(
            match_report_id=arguments.match_report_id,
            deadline=arguments.deadline,
        )
        return StudyPlanRead.model_validate(plan).model_dump(mode="json")

    return (
        ToolSpec(
            name="get_job_requirements",
            description="读取一个已分析岗位的结构化技能、职责和证据。",
            input_model=GetJobRequirementsInput,
            handler=get_job_requirements,
        ),
        ToolSpec(
            name="compare_resume_with_job",
            description="比较指定简历与岗位要求，返回匹配技能和缺口。",
            input_model=CompareResumeWithJobInput,
            handler=compare_resume_with_job,
        ),
        ToolSpec(
            name="search_learning_material",
            description="在本地知识库中语义检索学习材料。",
            input_model=SearchLearningMaterialInput,
            handler=search_learning_material,
        ),
        ToolSpec(
            name="create_study_plan",
            description="基于不可变匹配报告的优先技能缺口创建规则学习计划。",
            input_model=CreateStudyPlanInput,
            handler=create_study_plan,
        ),
    )
