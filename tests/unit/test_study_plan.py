"""学习计划规则与服务测试。"""

from datetime import UTC, date, datetime

import pytest

from app.core.config import Settings
from app.core.database import Database
from app.core.exceptions import (
    InsufficientKnowledgeError,
    InvalidStudyTaskTransitionError,
    KnowledgeUnavailableError,
    NoPrioritySkillsError,
    StudyPlanConflictError,
    StudyPlanGenerationError,
    StudyPlanValidationError,
)
from app.models.enums import DocumentStatus, StudyPlanStatus, StudyTaskPhase, StudyTaskStatus
from app.models.job import Job
from app.models.knowledge_document import KnowledgeDocument
from app.models.match_report import MatchReportRow
from app.models.resume import Resume
from app.schemas.knowledge import KnowledgeSearchResponse, KnowledgeSearchResult
from app.services.study_plan import StudyPlanService, generate_rule_v1_tasks


class FakePlanSearch:
    """按技能返回确定性内置资料片段。"""

    def __init__(self, results: dict[str, list[KnowledgeSearchResult]]) -> None:
        self.results = results
        self.document_ids: list[list[int] | None] = []

    def search(self, *, query, top_k, document_ids, max_distance=None):
        del top_k, max_distance
        self.document_ids.append(document_ids)
        return KnowledgeSearchResponse(
            query=query,
            max_distance=0.45,
            results=self.results.get(query, []),
        )


class FakePlanClient:
    """返回测试指定的结构化学习计划。"""

    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def complete_structured(self, *, prompt, response_model):
        assert "untrusted data" in prompt
        return response_model.model_validate(self.payload)


def _evidence(skill: str) -> KnowledgeSearchResult:
    return KnowledgeSearchResult(
        chunk_id=f"document:1:chunk:{skill}",
        document_id=1,
        source_name="AI-Agents-in-Depth-zh-CN.pdf",
        chunk_index=1,
        text=f"{skill} 的真实资料片段",
        distance=0.2,
    )


def _add_builtin_document(session) -> int:
    document = KnowledgeDocument(
        source_name="AI-Agents-in-Depth-zh-CN.pdf",
        content_type="application/pdf",
        raw_text="电子 PDF 正文",
        status=DocumentStatus.READY,
        chunk_count=2,
        is_builtin=True,
        approved=True,
        source_sha256="a" * 64,
        content_sha256="b" * 64,
        embedding_model="test-model",
        chunk_size=500,
        chunk_overlap=80,
    )
    session.add(document)
    session.commit()
    return document.id


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


def test_rag_v1_saves_grounded_tasks_partial_coverage_and_reuses_existing(tmp_path) -> None:
    database = Database(
        Settings(environment="test", database_url=f"sqlite:///{tmp_path / 'rag-plan.db'}")
    )
    database.create_all()
    try:
        with database.session() as session:
            report_id = _add_report(
                session,
                priority_skills=[
                    {"skill": "Agent", "evidence": "需要 Agent"},
                    {"skill": "Docker", "evidence": "需要 Docker"},
                ],
            )
            document_id = _add_builtin_document(session)
            search = FakePlanSearch({"Agent": [_evidence("Agent")]})
            client = FakePlanClient(
                {
                    "skills": [
                        {
                            "skill": "Agent",
                            "support_status": "supported",
                            "tasks": [
                                {
                                    "phase": "learn",
                                    "title": "理解 Agent 的规划循环",
                                    "learning_content": "理解观察、决策与执行的循环。",
                                    "action": "画出一次循环的数据流。",
                                    "completion_criteria": "能解释三个阶段的输入输出。",
                                    "evidence_ids": ["document:1:chunk:Agent"],
                                }
                            ],
                        }
                    ]
                }
            )
            service = StudyPlanService(session, date_provider=lambda: date(2026, 9, 9))

            result = service.create_rag(
                match_report_id=report_id,
                deadline=None,
                search_service=search,
                client=client,
                builtin_document_ids=[document_id],
                model_name="fake-model",
                prompt_version="study-plan-rag-v1",
            )

            assert result.created is True
            assert result.plan.generation_method == "rag_v1"
            assert result.plan.coverage == {
                "target_skills": ["Agent", "Docker"],
                "covered_skills": ["Agent"],
                "uncovered_skills": [{"skill": "Docker", "reason_code": "no_relevant_evidence"}],
            }
            assert result.plan.tasks[0].learning_content.startswith("理解")
            assert result.plan.tasks[0].action.startswith("画出")
            assert result.plan.tasks[0].resource_query is None
            assert result.plan.tasks[0].evidence[0]["source_name"].endswith(".pdf")
            assert search.document_ids == [[document_id], [document_id]]

            reused = service.create_rag(
                match_report_id=report_id,
                deadline=date(2026, 10, 1),
                search_service=FakePlanSearch({}),
                client=client,
                builtin_document_ids=[],
                model_name="ignored",
                prompt_version="ignored",
            )
            assert reused.created is False
            assert reused.plan.id == result.plan.id
            assert reused.plan.deadline is None
    finally:
        database.dispose()


def test_rag_v1_rejects_empty_knowledge_unknown_evidence_and_unready_config(tmp_path) -> None:
    database = Database(
        Settings(environment="test", database_url=f"sqlite:///{tmp_path / 'rag-errors.db'}")
    )
    database.create_all()
    try:
        with database.session() as session:
            report_id = _add_report(
                session,
                priority_skills=[{"skill": "Agent", "evidence": None}],
            )
            empty_report_id = _add_report(session, priority_skills=[])
            document_id = _add_builtin_document(session)
            service = StudyPlanService(session)

            common = {
                "deadline": None,
                "model_name": "fake",
                "prompt_version": "v1",
            }
            with pytest.raises(NoPrioritySkillsError):
                service.create_rag(
                    match_report_id=empty_report_id,
                    search_service=FakePlanSearch({}),
                    client=FakePlanClient({"skills": []}),
                    builtin_document_ids=[document_id],
                    **common,
                )
            with pytest.raises(KnowledgeUnavailableError):
                service.create_rag(
                    match_report_id=report_id,
                    search_service=FakePlanSearch({}),
                    client=FakePlanClient({"skills": []}),
                    builtin_document_ids=[],
                    **common,
                )
            with pytest.raises(InsufficientKnowledgeError):
                service.create_rag(
                    match_report_id=report_id,
                    search_service=FakePlanSearch({}),
                    client=FakePlanClient({"skills": []}),
                    builtin_document_ids=[document_id],
                    **common,
                )
            with pytest.raises(StudyPlanGenerationError, match="unknown evidence"):
                service.create_rag(
                    match_report_id=report_id,
                    search_service=FakePlanSearch({"Agent": [_evidence("Agent")]}),
                    client=FakePlanClient(
                        {
                            "skills": [
                                {
                                    "skill": "Agent",
                                    "support_status": "supported",
                                    "tasks": [
                                        {
                                            "phase": "learn",
                                            "title": "Agent",
                                            "learning_content": "内容",
                                            "action": "行动",
                                            "completion_criteria": "标准",
                                            "evidence_ids": ["unknown"],
                                        }
                                    ],
                                }
                            ]
                        }
                    ),
                    builtin_document_ids=[document_id],
                    **common,
                )
            assert service.plan_repository.get_by_match_report(report_id) is None
    finally:
        database.dispose()
