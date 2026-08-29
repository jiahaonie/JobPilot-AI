"""Real application handlers exposed to the model-selected tool workflow."""

from sqlalchemy.orm import Session

from app.agents.tools import (
    CompareResumeWithJobInput,
    GetJobRequirementsInput,
    SearchLearningMaterialInput,
    ToolSpec,
)
from app.core.exceptions import JobRequirementNotFoundError
from app.repositories.job_requirement import JobRequirementRepository
from app.schemas.requirements import JobRequirement
from app.services.matching import MatchService
from app.services.search import KnowledgeSearchService


def build_real_tool_specs(
    *,
    session: Session,
    search_service: KnowledgeSearchService,
) -> tuple[ToolSpec, ...]:
    """Bind three model-visible tools to real repositories and services."""

    requirement_repository = JobRequirementRepository(session)
    match_service = MatchService(session)

    def get_job_requirements(arguments: GetJobRequirementsInput) -> dict:
        row = requirement_repository.get_by_job(arguments.job_id)
        if row is None:
            raise JobRequirementNotFoundError(
                f"Job {arguments.job_id} has not been analyzed yet"
            )
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
    )
