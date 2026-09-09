"""学习计划与任务 HTTP 接口测试。"""

import json
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi import FastAPI
from sqlalchemy import func, select

from app.api.dependencies import get_builtin_knowledge_search_service
from app.models.enums import DocumentStatus
from app.models.job import Job
from app.models.knowledge_document import KnowledgeDocument
from app.models.match_report import MatchReportRow
from app.models.resume import Resume
from app.models.study_plan import StudyPlan
from app.models.study_task import StudyTask
from app.schemas.knowledge import KnowledgeSearchResponse, KnowledgeSearchResult


class FakeSearch:
    """为任意技能返回属于配置文档的片段。"""

    def __init__(self, document_id: int) -> None:
        self.document_id = document_id

    def search(self, *, query, top_k, document_ids, max_distance=None):
        del top_k, max_distance
        assert document_ids == [self.document_id]
        return KnowledgeSearchResponse(
            query=query,
            max_distance=0.45,
            results=[
                KnowledgeSearchResult(
                    chunk_id=f"document:{self.document_id}:chunk:{query}",
                    document_id=self.document_id,
                    source_name="AI-Agents-in-Depth-zh-CN.pdf",
                    chunk_index=0,
                    text=f"{query} 的依据",
                    distance=0.1,
                )
            ],
        )


class FakePlanClient:
    """从提示词目标技能生成一项可校验任务。"""

    def complete_structured(self, *, prompt, response_model):
        skill_payload = prompt.split("<target_skills>\n", 1)[1].split(
            "\n</target_skills>", 1
        )[0]
        document_id = prompt.split("document:", 1)[1].split(":", 1)[0]
        skills = json.loads(skill_payload)
        return response_model.model_validate(
            {
                "skills": [
                    {
                        "skill": skill,
                        "support_status": "supported",
                        "tasks": [
                            {
                                "phase": "learn",
                                "title": f"理解 {skill} 的核心机制",
                                "learning_content": f"理解 {skill} 的资料内容。",
                                "action": f"整理 {skill} 的数据流。",
                                "completion_criteria": "能够结合原文解释关键步骤。",
                                "evidence_ids": [f"document:{document_id}:chunk:{skill}"],
                            }
                        ],
                    }
                    for skill in skills
                ]
            }
        )


def _configure_rag(application: FastAPI) -> int:
    """为接口测试装配一份已审核资料和可控的检索、生成替身。"""
    with application.state.database.session() as session:
        document = KnowledgeDocument(
            source_name="AI-Agents-in-Depth-zh-CN.pdf",
            content_type="application/pdf",
            raw_text="测试正文",
            status=DocumentStatus.READY,
            chunk_count=3,
            is_builtin=True,
            approved=True,
            source_sha256="a" * 64,
            content_sha256="b" * 64,
        )
        session.add(document)
        session.commit()
        document_id = document.id
    application.state.settings.rag_builtin_document_ids = str(document_id)
    application.state.llm_client = FakePlanClient()
    application.dependency_overrides[get_builtin_knowledge_search_service] = (
        lambda: FakeSearch(document_id)
    )
    return document_id


def _seed_report(
    application: FastAPI,
    *,
    priority_skills: list[dict],
    company_name: str = "Example",
) -> tuple[int, int, int]:
    """创建接口测试所需的岗位、简历和匹配报告。"""
    with application.state.database.session() as session:
        job = Job(
            company_name=company_name,
            job_title="AI Intern",
            raw_text="需要 Python、FastAPI 和 Docker。",
        )
        resume = Resume(
            title=f"{company_name} candidate",
            raw_text="掌握 Python。",
            skills=["Python"],
        )
        session.add_all([job, resume])
        session.flush()
        report = MatchReportRow(
            job_id=job.id,
            resume_id=resume.id,
            skill_coverage_score=33.3,
            required_score=33.3,
            preferred_score=None,
            score_disclaimer="仅表示技能覆盖程度。",
            matched_skills=["Python"],
            bonus_skills=[],
            missing_skills=priority_skills,
            priority_skills=priority_skills,
            required_skills_snapshot=["Python", "FastAPI", "Docker"],
            preferred_skills_snapshot=[],
            resume_skills_snapshot=["Python"],
            job_requirement_updated_at=datetime.now(UTC),
            resume_analyzed_at=datetime.now(UTC),
            scoring_version="skill-coverage-v1",
        )
        session.add(report)
        session.commit()
        return report.id, job.id, resume.id


def test_create_get_and_filter_study_plan(application, client) -> None:
    _configure_rag(application)
    report_id, job_id, resume_id = _seed_report(
        application,
        priority_skills=[
            {"skill": "Docker", "evidence": "需要 Docker"},
            {"skill": "FastAPI", "evidence": "需要 FastAPI"},
            {"skill": "RAG", "evidence": None},
        ],
    )
    deadline = date.today() + timedelta(days=8)

    response = client.post(
        "/api/v1/study-plans",
        json={
            "match_report_id": report_id,
            "deadline": deadline.isoformat(),
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["match_report_id"] == report_id
    assert payload["generation_method"] == "rag_v1"
    assert payload["status"] == "not_started"
    assert payload["completed_count"] == 0
    assert payload["task_count"] == 3
    assert [task["position"] for task in payload["tasks"]] == [1, 2, 3]
    assert [task["phase"] for task in payload["tasks"]] == ["learn"] * 3
    assert payload["coverage"]["covered_skills"] == ["Docker", "FastAPI", "RAG"]
    assert payload["tasks"][0]["evidence"][0]["source_name"].endswith(".pdf")
    assert payload["tasks"][0]["due_date"] == date.today().isoformat()
    assert payload["tasks"][-1]["due_date"] == deadline.isoformat()

    plan_id = payload["id"]
    assert client.get(f"/api/v1/study-plans/{plan_id}").json() == payload
    by_job = client.get(f"/api/v1/study-plans?job_id={job_id}")
    by_resume = client.get(f"/api/v1/study-plans?resume_id={resume_id}")
    by_report = client.get(f"/api/v1/study-plans?match_report_id={report_id}")
    assert [item["id"] for item in by_job.json()] == [plan_id]
    assert [item["id"] for item in by_resume.json()] == [plan_id]
    assert [item["id"] for item in by_report.json()] == [plan_id]


def test_create_study_plan_rejects_missing_empty_duplicate_and_past_deadline(
    application,
    client,
) -> None:
    _configure_rag(application)
    report_id, _, _ = _seed_report(
        application,
        priority_skills=[
            {"skill": "Docker", "evidence": None},
            {"skill": "FastAPI", "evidence": None},
        ],
    )
    empty_report_id, _, _ = _seed_report(
        application,
        priority_skills=[],
        company_name="Empty",
    )

    assert (
        client.post(
            "/api/v1/study-plans",
            json={"match_report_id": 999_999},
        ).status_code
        == 404
    )
    empty_response = client.post(
        "/api/v1/study-plans",
        json={"match_report_id": empty_report_id},
    )
    assert empty_response.status_code == 409
    assert empty_response.json()["code"] == "NO_PRIORITY_SKILLS"
    assert (
        client.post(
            "/api/v1/study-plans",
            json={
                "match_report_id": report_id,
                "deadline": (date.today() - timedelta(days=1)).isoformat(),
            },
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/study-plans",
            json={"match_report_id": report_id},
        ).status_code
        == 201
    )
    duplicate = client.post(
        "/api/v1/study-plans",
        json={"match_report_id": report_id},
    )
    assert duplicate.status_code == 200


def test_update_task_status_and_recalculate_plan_progress(application, client) -> None:
    _configure_rag(application)
    report_id, _, _ = _seed_report(
        application,
        priority_skills=[
            {"skill": "Docker", "evidence": None},
            {"skill": "FastAPI", "evidence": None},
        ],
    )
    plan = client.post(
        "/api/v1/study-plans",
        json={"match_report_id": report_id},
    ).json()
    task_ids = [task["id"] for task in plan["tasks"]]

    first_done = client.patch(
        f"/api/v1/study-tasks/{task_ids[0]}",
        json={"status": "done"},
    )
    assert first_done.status_code == 200
    assert first_done.json()["completed_at"] is not None
    assert client.get(f"/api/v1/study-plans/{plan['id']}").json()["status"] == "in_progress"

    invalid = client.patch(
        f"/api/v1/study-tasks/{task_ids[0]}",
        json={"status": "todo"},
    )
    assert invalid.status_code == 409
    assert client.patch("/api/v1/study-tasks/999999", json={"status": "done"}).status_code == 404
    assert client.patch(
        f"/api/v1/study-tasks/{task_ids[1]}",
        json={"status": "invalid"},
    ).status_code == 422

    for task_id in task_ids[1:]:
        assert client.patch(
            f"/api/v1/study-tasks/{task_id}",
            json={"status": "done"},
        ).status_code == 200

    completed = client.get(f"/api/v1/study-plans/{plan['id']}").json()
    assert completed["status"] == "completed"
    assert completed["completed_count"] == completed["task_count"] == 2

    reopened = client.patch(
        f"/api/v1/study-tasks/{task_ids[0]}",
        json={"status": "in_progress"},
    )
    assert reopened.status_code == 200
    assert reopened.json()["completed_at"] is None


@pytest.mark.parametrize("delete_target", ["job", "resume", "report", "plan"])
def test_deletion_cascades_follow_confirmed_ownership(
    application,
    client,
    delete_target,
) -> None:
    _configure_rag(application)
    report_id, job_id, resume_id = _seed_report(
        application,
        priority_skills=[
            {"skill": "Docker", "evidence": None},
        ],
    )
    response = client.post(
        "/api/v1/study-plans",
        json={"match_report_id": report_id},
    )
    assert response.status_code == 201
    plan_id = response.json()["id"]

    with application.state.database.session() as session:
        targets = {
            "job": session.get(Job, job_id),
            "resume": session.get(Resume, resume_id),
            "report": session.get(MatchReportRow, report_id),
            "plan": session.get(StudyPlan, plan_id),
        }
        session.delete(targets[delete_target])
        session.commit()

        expected_report_count = 1 if delete_target == "plan" else 0
        assert (
            session.scalar(select(func.count()).select_from(MatchReportRow))
            == expected_report_count
        )
        assert session.scalar(select(func.count()).select_from(StudyPlan)) == 0
        assert session.scalar(select(func.count()).select_from(StudyTask)) == 0
