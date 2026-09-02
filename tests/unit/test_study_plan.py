"""学习计划规则与服务测试。"""

from datetime import UTC, date, datetime

import pytest

from app.core.config import Settings
from app.core.database import Database
from app.core.exceptions import (
    InvalidStudyTaskTransitionError,
    StudyPlanConflictError,
    StudyPlanValidationError,
)
from app.models.enums import StudyPlanStatus, StudyTaskPhase, StudyTaskStatus
from app.models.job import Job
from app.models.match_report import MatchReportRow
from app.models.resume import Resume
from app.services.study_plan import StudyPlanService, generate_rule_v1_tasks


def _add_report(session, *, priority_skills: list[dict]) -> int:
    """创建学习计划测试所需的最小匹配报告。"""
    job = Job(
        company_name="Example",
        job_title="AI Intern",
        raw_text="需要 Python 和 Docker。",
    )
    resume = Resume(
        title="candidate",
        raw_text="掌握 Python。",
        skills=["Python"],
    )
    session.add_all([job, resume])
    session.flush()
    report = MatchReportRow(
        job_id=job.id,
        resume_id=resume.id,
        skill_coverage_score=50.0,
        required_score=50.0,
        preferred_score=None,
        score_disclaimer="仅表示技能覆盖程度。",
        matched_skills=["Python"],
        bonus_skills=[],
        missing_skills=priority_skills,
        priority_skills=priority_skills,
        required_skills_snapshot=["Python", "Docker"],
        preferred_skills_snapshot=[],
        resume_skills_snapshot=["Python"],
        job_requirement_updated_at=datetime.now(UTC),
        resume_analyzed_at=datetime.now(UTC),
        scoring_version="skill-coverage-v1",
    )
    session.add(report)
    session.commit()
    return report.id


def test_rule_v1_generates_three_ordered_tasks_per_skill() -> None:
    start = date(2026, 9, 2)
    deadline = date(2026, 9, 12)

    tasks = generate_rule_v1_tasks(
        ["Docker", "FastAPI"],
        start_date=start,
        deadline=deadline,
    )

    assert len(tasks) == 6
    assert [task.position for task in tasks] == list(range(1, 7))
    assert [task.phase for task in tasks[:3]] == [
        StudyTaskPhase.LEARN,
        StudyTaskPhase.PRACTICE,
        StudyTaskPhase.VERIFY,
    ]
    assert [task.skill for task in tasks] == ["Docker"] * 3 + ["FastAPI"] * 3
    assert tasks[0].title == "学习 Docker 核心概念"
    assert tasks[0].resource_query == "Docker 入门与实践"
    assert tasks[0].due_date == start
    assert tasks[-1].due_date == deadline
    assert [task.due_date for task in tasks] == sorted(task.due_date for task in tasks)


def test_rule_v1_keeps_due_dates_empty_without_deadline() -> None:
    tasks = generate_rule_v1_tasks(
        ["Docker"],
        start_date=date(2026, 9, 2),
        deadline=None,
    )

    assert [task.due_date for task in tasks] == [None, None, None]


def test_service_creates_plan_and_rejects_duplicate_or_empty_report(tmp_path) -> None:
    database = Database(
        Settings(
            environment="test",
            database_url=f"sqlite:///{tmp_path / 'study-plan.db'}",
        )
    )
    database.create_all()
    try:
        with database.session() as session:
            report_id = _add_report(
                session,
                priority_skills=[
                    {"skill": "Docker", "evidence": "需要 Docker"},
                ],
            )
            empty_report_id = _add_report(session, priority_skills=[])
            service = StudyPlanService(
                session,
                date_provider=lambda: date(2026, 9, 2),
            )

            plan = service.create(
                match_report_id=report_id,
                deadline=date(2026, 9, 4),
            )

            assert plan.generation_method == "rule_v1"
            assert plan.status is StudyPlanStatus.NOT_STARTED
            assert plan.task_count == 3
            assert plan.completed_count == 0
            assert [task.due_date for task in plan.tasks] == [
                date(2026, 9, 2),
                date(2026, 9, 3),
                date(2026, 9, 4),
            ]
            with pytest.raises(StudyPlanConflictError, match="already has"):
                service.create(match_report_id=report_id)
            with pytest.raises(StudyPlanConflictError, match="no priority skills"):
                service.create(match_report_id=empty_report_id)
            with pytest.raises(StudyPlanValidationError, match="earlier"):
                service.create(
                    match_report_id=empty_report_id,
                    deadline=date(2026, 9, 1),
                )
    finally:
        database.dispose()


def test_task_state_machine_updates_completion_time_and_plan_progress(tmp_path) -> None:
    database = Database(
        Settings(
            environment="test",
            database_url=f"sqlite:///{tmp_path / 'task-status.db'}",
        )
    )
    database.create_all()
    completed_at = datetime(2026, 9, 2, 8, 30, tzinfo=UTC)
    try:
        with database.session() as session:
            report_id = _add_report(
                session,
                priority_skills=[
                    {"skill": "Docker", "evidence": None},
                ],
            )
            service = StudyPlanService(
                session,
                date_provider=lambda: date(2026, 9, 2),
                datetime_provider=lambda: completed_at,
            )
            plan = service.create(match_report_id=report_id)
            first_task = plan.tasks[0]

            service.update_task(
                task_id=first_task.id,
                target=StudyTaskStatus.DONE,
            )

            assert first_task.completed_at == completed_at.replace(tzinfo=None)
            assert service.get(plan.id).status is StudyPlanStatus.IN_PROGRESS
            with pytest.raises(InvalidStudyTaskTransitionError):
                service.update_task(
                    task_id=first_task.id,
                    target=StudyTaskStatus.TODO,
                )

            service.update_task(
                task_id=first_task.id,
                target=StudyTaskStatus.IN_PROGRESS,
            )
            assert first_task.completed_at is None
            service.update_task(
                task_id=first_task.id,
                target=StudyTaskStatus.TODO,
            )
            service.update_task(
                task_id=first_task.id,
                target=StudyTaskStatus.IN_PROGRESS,
            )

            for task in plan.tasks:
                if task.status in {
                    StudyTaskStatus.TODO,
                    StudyTaskStatus.IN_PROGRESS,
                }:
                    service.update_task(
                        task_id=task.id,
                        target=StudyTaskStatus.DONE,
                    )

            completed_plan = service.get(plan.id)
            assert completed_plan.status is StudyPlanStatus.COMPLETED
            assert completed_plan.completed_count == completed_plan.task_count
    finally:
        database.dispose()
