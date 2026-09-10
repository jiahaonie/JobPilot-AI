"""基于不可变匹配报告生成并维护学习计划。"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from time import perf_counter

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    InsufficientKnowledgeError,
    InvalidStudyTaskTransitionError,
    KnowledgeUnavailableError,
    NoPrioritySkillsError,
    ResourceNotFoundError,
    StudyPlanConflictError,
    StudyPlanGenerationError,
    StudyPlanGenerationTimeoutError,
    StudyPlanPersistenceError,
    StudyPlanValidationError,
)
from app.llm.client import StructuredLLMClient
from app.llm.exceptions import LLMError, LLMTimeoutError
from app.llm.prompts import build_study_plan_prompt
from app.models.enums import DocumentStatus, StudyTaskPhase, StudyTaskStatus
from app.models.knowledge_document import KnowledgeDocument
from app.models.study_plan import StudyPlan
from app.models.study_task import StudyTask
from app.repositories.match_report import MatchReportRepository
from app.repositories.study_plan import StudyPlanRepository
from app.schemas.matching import SkillGap
from app.schemas.study_plan import GeneratedStudyPlan
from app.services.search import KnowledgeSearchService

RULE_GENERATION_METHOD = "rule_v1"
RAG_GENERATION_METHOD = "rag_v1"

_TASK_TEMPLATES = (
    (
        StudyTaskPhase.LEARN,
        "学习 {skill} 核心概念",
        "整理该技能的关键概念笔记",
    ),
    (
        StudyTaskPhase.PRACTICE,
        "完成 {skill} 最小实践",
        "产出一个可以运行或复现的示例",
    ),
    (
        StudyTaskPhase.VERIFY,
        "在项目中应用 {skill}",
        "提交代码、测试结果或复盘记录",
    ),
)

_ALLOWED_TASK_TRANSITIONS: dict[StudyTaskStatus, set[StudyTaskStatus]] = {
    StudyTaskStatus.TODO: {
        StudyTaskStatus.IN_PROGRESS,
        StudyTaskStatus.DONE,
    },
    StudyTaskStatus.IN_PROGRESS: {
        StudyTaskStatus.TODO,
        StudyTaskStatus.DONE,
    },
    StudyTaskStatus.DONE: {StudyTaskStatus.IN_PROGRESS},
}


@dataclass(frozen=True)
class StudyTaskBlueprint:
    """规则生成后、持久化前的一项任务数据。"""

    skill: str
    phase: StudyTaskPhase
    title: str
    completion_criteria: str
    resource_query: str
    position: int
    due_date: date | None


@dataclass(frozen=True)
class StudyPlanCreationResult:
    """区分首次持久化与幂等返回已有计划。"""

    plan: StudyPlan
    created: bool


def generate_rule_v1_tasks(
    skills: Sequence[str],
    *,
    start_date: date,
    deadline: date | None,
) -> list[StudyTaskBlueprint]:
    """按技能原始顺序为每项技能生成学习、实践和验证任务。"""
    task_data = [
        (skill, phase, title_template, criteria)
        for skill in skills
        for phase, title_template, criteria in _TASK_TEMPLATES
    ]
    due_dates = _distribute_due_dates(
        task_count=len(task_data),
        start_date=start_date,
        deadline=deadline,
    )
    return [
        StudyTaskBlueprint(
            skill=skill,
            phase=phase,
            title=title_template.format(skill=skill),
            completion_criteria=criteria,
            resource_query=f"{skill} 入门与实践",
            position=index,
            due_date=due_dates[index - 1],
        )
        for index, (skill, phase, title_template, criteria) in enumerate(
            task_data,
            start=1,
        )
    ]


def _distribute_due_dates(
    *,
    task_count: int,
    start_date: date,
    deadline: date | None,
) -> list[date | None]:
    """在起止日期之间按任务顺序确定性分配到期日。"""
    if deadline is None:
        return [None] * task_count
    if task_count == 0:
        return []
    if task_count == 1:
        return [deadline]

    span_days = (deadline - start_date).days
    return [
        start_date + timedelta(days=(index * span_days) // (task_count - 1))
        for index in range(task_count)
    ]


class StudyPlanService:
    """创建、查询学习计划并维护任务状态。"""

    def __init__(
        self,
        session: Session,
        *,
        date_provider: Callable[[], date] | None = None,
        datetime_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self.session = session
        self.date_provider = date_provider or date.today
        self.datetime_provider = datetime_provider or (lambda: datetime.now(UTC))
        self.match_report_repository = MatchReportRepository(session)
        self.plan_repository = StudyPlanRepository(session)

    def create(
        self,
        *,
        match_report_id: int,
        deadline: date | None = None,
    ) -> StudyPlan:
        """使用 rule_v1 为一份匹配报告创建且只创建一份计划。"""
        today = self.date_provider()
        if deadline is not None and deadline < today:
            raise StudyPlanValidationError("deadline cannot be earlier than today")

        report = self.match_report_repository.get(match_report_id)
        if report is None:
            raise ResourceNotFoundError(f"Match report {match_report_id} was not found")
        if self.plan_repository.get_by_match_report(match_report_id) is not None:
            raise StudyPlanConflictError(f"Match report {match_report_id} already has a study plan")

        skills = self._priority_skills(report.priority_skills)
        if not skills:
            raise StudyPlanConflictError(f"Match report {match_report_id} has no priority skills")

        plan = StudyPlan(
            match_report_id=match_report_id,
            deadline=deadline,
            generation_method=RULE_GENERATION_METHOD,
        )
        plan.tasks = [
            StudyTask(
                skill=blueprint.skill,
                phase=blueprint.phase,
                title=blueprint.title,
                completion_criteria=blueprint.completion_criteria,
                resource_query=blueprint.resource_query,
                position=blueprint.position,
                status=StudyTaskStatus.TODO,
                due_date=blueprint.due_date,
            )
            for blueprint in generate_rule_v1_tasks(
                skills,
                start_date=today,
                deadline=deadline,
            )
        ]
        try:
            self.plan_repository.add(plan)
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            if self.plan_repository.get_by_match_report(match_report_id) is not None:
                raise StudyPlanConflictError(
                    f"Match report {match_report_id} already has a study plan"
                ) from exc
            raise StudyPlanPersistenceError("Study plan could not be saved") from exc
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise StudyPlanPersistenceError("Study plan could not be saved") from exc
        return self.get(plan.id)

    def create_rag(
        self,
        *,
        match_report_id: int,
        deadline: date | None,
        search_service: KnowledgeSearchService,
        client: StructuredLLMClient,
        builtin_document_ids: list[int],
        model_name: str,
        prompt_version: str,
        top_k: int = 5,
        context_char_limit: int = 30_000,
        time_budget_seconds: float = 120.0,
    ) -> StudyPlanCreationResult:
        """从受控内置资料生成、校验并原子保存一份 rag_v1 计划。"""
        started_at = perf_counter()
        report = self.match_report_repository.get(match_report_id)
        if report is None:
            raise ResourceNotFoundError(f"Match report {match_report_id} was not found")
        existing = self.plan_repository.get_by_match_report(match_report_id)
        if existing is not None:
            return StudyPlanCreationResult(plan=existing, created=False)

        today = self.date_provider()
        if deadline is not None and deadline < today:
            raise StudyPlanValidationError("deadline cannot be earlier than today")
        skills = self._priority_skills(report.priority_skills)
        if not skills:
            raise NoPrioritySkillsError(
                "Current report has no priority skills and does not need a study plan"
            )

        documents = self._ready_builtin_documents(builtin_document_ids)
        candidates: dict[str, list] = {}
        uncovered_reasons: dict[str, str] = {}
        try:
            for skill in skills:
                if perf_counter() - started_at >= time_budget_seconds:
                    raise StudyPlanGenerationTimeoutError("Study plan generation timed out")
                response = search_service.search(
                    query=skill,
                    top_k=top_k,
                    document_ids=builtin_document_ids,
                )
                if response.results:
                    candidates[skill] = response.results
                else:
                    uncovered_reasons[skill] = "no_relevant_evidence"
        except Exception as exc:
            raise KnowledgeUnavailableError("Built-in knowledge search is unavailable") from exc

        if not candidates:
            raise InsufficientKnowledgeError(
                "Built-in knowledge does not support any priority skill",
                uncovered_skills=self._uncovered_skills(skills, uncovered_reasons),
            )

        context_chars = sum(
            len(result.text) for results in candidates.values() for result in results
        )
        if context_chars > context_char_limit:
            raise StudyPlanGenerationError(
                "Study plan evidence exceeds the configured context limit"
            )

        candidate_skills = list(candidates)
        prompt = build_study_plan_prompt(
            candidate_skills,
            {
                skill: [(result.chunk_id, result.text) for result in candidates[skill]]
                for skill in candidate_skills
            },
        )
        try:
            generated = client.complete_structured(
                prompt=prompt,
                response_model=GeneratedStudyPlan,
            )
        except LLMTimeoutError as exc:
            raise StudyPlanGenerationTimeoutError("Study plan generation timed out") from exc
        except LLMError as exc:
            raise StudyPlanGenerationError("Study plan generation failed") from exc
        if perf_counter() - started_at >= time_budget_seconds:
            raise StudyPlanGenerationTimeoutError("Study plan generation timed out")

        if [item.skill for item in generated.skills] != candidate_skills:
            raise StudyPlanGenerationError(
                "Generated plan omitted, added, duplicated, or reordered target skills"
            )

        task_rows: list[dict] = []
        covered: list[str] = []
        for skill_plan in generated.skills:
            if skill_plan.support_status == "insufficient_support":
                uncovered_reasons[skill_plan.skill] = "insufficient_support"
                continue
            result_by_id = {result.chunk_id: result for result in candidates[skill_plan.skill]}
            for task in skill_plan.tasks:
                if len(set(task.evidence_ids)) != len(task.evidence_ids) or any(
                    evidence_id not in result_by_id for evidence_id in task.evidence_ids
                ):
                    raise StudyPlanGenerationError(
                        f"Generated task for {skill_plan.skill} cited unknown evidence"
                    )
                task_rows.append(
                    {
                        "skill": skill_plan.skill,
                        "phase": task.phase,
                        "title": task.title.strip(),
                        "learning_content": task.learning_content.strip(),
                        "action": task.action.strip(),
                        "completion_criteria": task.completion_criteria.strip(),
                        "evidence": [
                            {
                                "chunk_id": evidence_id,
                                "document_id": result_by_id[evidence_id].document_id,
                                "source_name": result_by_id[evidence_id].source_name,
                                "excerpt": result_by_id[evidence_id].text,
                                "location": None,
                            }
                            for evidence_id in task.evidence_ids
                        ],
                    }
                )
            covered.append(skill_plan.skill)

        if not task_rows:
            raise InsufficientKnowledgeError(
                "Built-in knowledge does not sufficiently support any priority skill",
                uncovered_skills=self._uncovered_skills(skills, uncovered_reasons),
            )

        due_dates = _distribute_due_dates(
            task_count=len(task_rows),
            start_date=today,
            deadline=deadline,
        )
        plan = StudyPlan(
            match_report_id=match_report_id,
            deadline=deadline,
            generation_method=RAG_GENERATION_METHOD,
            coverage={
                "target_skills": skills,
                "covered_skills": covered,
                "uncovered_skills": self._uncovered_skills(skills, uncovered_reasons),
            },
            generation_metadata={
                "model": model_name,
                "prompt_version": prompt_version,
                "documents": [
                    {
                        "id": document.id,
                        "source_sha256": document.source_sha256,
                        "content_sha256": document.content_sha256,
                    }
                    for document in documents
                ],
            },
        )
        plan.tasks = [
            StudyTask(
                **row,
                resource_query=None,
                position=index,
                status=StudyTaskStatus.TODO,
                due_date=due_dates[index - 1],
            )
            for index, row in enumerate(task_rows, start=1)
        ]
        try:
            winner = self.plan_repository.get_by_match_report(match_report_id)
            if winner is not None:
                return StudyPlanCreationResult(plan=winner, created=False)
            self.plan_repository.add(plan)
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            winner = self.plan_repository.get_by_match_report(match_report_id)
            if winner is not None:
                return StudyPlanCreationResult(plan=winner, created=False)
            raise StudyPlanPersistenceError("Study plan could not be saved") from exc
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise StudyPlanPersistenceError("Study plan could not be saved") from exc
        return StudyPlanCreationResult(plan=self.get(plan.id), created=True)

    def get(self, plan_id: int) -> StudyPlan:
        """返回一份学习计划及其有序任务。"""
        plan = self.plan_repository.get(plan_id)
        if plan is None:
            raise ResourceNotFoundError(f"Study plan {plan_id} was not found")
        return plan

    def list_all(
        self,
        *,
        match_report_id: int | None = None,
        job_id: int | None = None,
        resume_id: int | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[StudyPlan]:
        """按可选岗位和简历筛选学习计划。"""
        return self.plan_repository.list(
            match_report_id=match_report_id,
            job_id=job_id,
            resume_id=resume_id,
            offset=offset,
            limit=limit,
        )

    def update_task(
        self,
        *,
        task_id: int,
        target: StudyTaskStatus,
    ) -> StudyTask:
        """按照受控状态机更新任务并维护完成时间。"""
        task = self.session.get(StudyTask, task_id)
        if task is None:
            raise ResourceNotFoundError(f"Study task {task_id} was not found")
        if task.status is target:
            return task
        if target not in _ALLOWED_TASK_TRANSITIONS[task.status]:
            raise InvalidStudyTaskTransitionError(
                f"Study task status cannot change from {task.status} to {target}"
            )

        changed_at = self.datetime_provider()
        task.status = target
        task.completed_at = changed_at if target is StudyTaskStatus.DONE else None
        task.study_plan.updated_at = changed_at
        try:
            self.session.commit()
            self.session.refresh(task)
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise StudyPlanPersistenceError("Study task could not be updated") from exc
        return task

    @staticmethod
    def _priority_skills(payload: list) -> list[str]:
        """兼容历史字符串，并校验当前匹配报告中的技能缺口快照。"""
        skills: list[str] = []
        try:
            for item in payload:
                skill = (
                    item.strip() if isinstance(item, str) else SkillGap.model_validate(item).skill
                )
                if skill and skill not in skills:
                    skills.append(skill)
        except (AttributeError, TypeError, ValidationError) as exc:
            raise StudyPlanConflictError("Match report priority skills are not usable") from exc
        return skills

    def _ready_builtin_documents(self, document_ids: list[int]) -> list[KnowledgeDocument]:
        """确认配置只引用已审核、已成功索引的内置资料。"""
        if not document_ids:
            raise KnowledgeUnavailableError("No built-in knowledge documents are configured")
        documents: list[KnowledgeDocument] = []
        for document_id in document_ids:
            document = self.session.get(KnowledgeDocument, document_id)
            if (
                document is None
                or document.status is not DocumentStatus.READY
                or not document.is_builtin
                or not document.approved
            ):
                raise KnowledgeUnavailableError(
                    f"Built-in knowledge document {document_id} is not ready and approved"
                )
            documents.append(document)
        return documents

    @staticmethod
    def _uncovered_skills(
        target_skills: list[str],
        reasons: dict[str, str],
    ) -> list[dict[str, str]]:
        """按报告原始技能顺序生成未覆盖快照。"""
        return [
            {"skill": skill, "reason_code": reasons[skill]}
            for skill in target_skills
            if skill in reasons
        ]
