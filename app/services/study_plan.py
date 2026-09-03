"""基于不可变匹配报告生成并维护学习计划。"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    InvalidStudyTaskTransitionError,
    ResourceNotFoundError,
    StudyPlanConflictError,
    StudyPlanPersistenceError,
    StudyPlanValidationError,
)
from app.models.enums import StudyTaskPhase, StudyTaskStatus
from app.models.study_plan import StudyPlan
from app.models.study_task import StudyTask
from app.repositories.match_report import MatchReportRepository
from app.repositories.study_plan import StudyPlanRepository
from app.schemas.matching import SkillGap

GENERATION_METHOD = "rule_v1"

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
            raise StudyPlanConflictError(
                f"Match report {match_report_id} already has a study plan"
            )

        skills = self._priority_skills(report.priority_skills)
        if not skills:
            raise StudyPlanConflictError(
                f"Match report {match_report_id} has no priority skills"
            )

        plan = StudyPlan(
            match_report_id=match_report_id,
            deadline=deadline,
            generation_method=GENERATION_METHOD,
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

    def get(self, plan_id: int) -> StudyPlan:
        """返回一份学习计划及其有序任务。"""
        plan = self.plan_repository.get(plan_id)
        if plan is None:
            raise ResourceNotFoundError(f"Study plan {plan_id} was not found")
        return plan

    def list_all(
        self,
        *,
        job_id: int | None = None,
        resume_id: int | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[StudyPlan]:
        """按可选岗位和简历筛选学习计划。"""
        return self.plan_repository.list(
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
                    item.strip()
                    if isinstance(item, str)
                    else SkillGap.model_validate(item).skill
                )
                if skill:
                    skills.append(skill)
        except (AttributeError, TypeError, ValidationError) as exc:
            raise StudyPlanConflictError(
                "Match report priority skills are not usable"
            ) from exc
        return skills
