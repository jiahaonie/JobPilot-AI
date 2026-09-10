"""简历与匹配 HTTP 流程的集成测试。"""

from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_db,
    get_job_analysis_service,
    get_llm_client,
)
from app.schemas.resume import MAX_RESUME_TEXT_CHARS
from app.services.analysis import JobAnalysisService


class FakeResumeLLM:
    def complete_structured(self, *, prompt, response_model):
        return response_model.model_validate({"skills": ["Python", "FastAPI"]})


class FakeAnalysisLLM:
    def complete_structured(self, *, prompt, response_model):
        return response_model.model_validate(
            {
                "job_title": "RAG Intern",
                "extraction_version": "job-requirements-v2",
                "skill_requirements": [
                    {
                        "label": "核心技能",
                        "importance": "required",
                        "match_mode": "all",
                        "options": ["Python", "FastAPI", "Vector DB"],
                        "evidence": ("Proficient in Python and FastAPI. Knowledge of Vector DB."),
                    },
                    {
                        "label": "NLP",
                        "importance": "preferred",
                        "match_mode": "all",
                        "options": ["NLP"],
                        "evidence": "NLP is preferred.",
                    },
                ],
                "unscored_requirements": [],
                "required_skills": [],
                "preferred_skills": [],
                "education": None,
                "internship_duration": None,
                "responsibilities": [],
                "evidence": ["Proficient in Python.", "Knowledge of Vector DB."],
            }
        )


def _override_llm(application, client) -> None:
    application.dependency_overrides[get_llm_client] = lambda: client


def _override_analysis(application, client) -> None:
    def override_service(db: Session = Depends(get_db)) -> JobAnalysisService:
        return JobAnalysisService(db, client)

    application.dependency_overrides[get_job_analysis_service] = override_service


def _create_job(client: TestClient) -> int:
    response = client.post(
        "/api/v1/jobs",
        json={
            "company_name": "Example Co",
            "job_title": "RAG Intern",
            "raw_text": (
                "Proficient in Python and FastAPI. Knowledge of Vector DB. NLP is preferred."
            ),
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_resume(client: TestClient) -> int:
    response = client.post(
        "/api/v1/resumes",
        json={"title": "我的简历", "raw_text": "熟悉 Python 和 FastAPI。"},
    )
    assert response.status_code == 201
    assert response.json()["analysis_status"] == "pending"
    return response.json()["id"]


def test_resume_creation_and_match_flow(application, client) -> None:
    _override_llm(application, FakeResumeLLM())
    _override_analysis(application, FakeAnalysisLLM())

    job_id = _create_job(client)
    analyze_response = client.post(f"/api/v1/jobs/{job_id}/analyze")
    assert analyze_response.status_code == 200
    resume_id = _create_resume(client)
    resume_analysis_response = client.post(f"/api/v1/resumes/{resume_id}/analyze")
    assert resume_analysis_response.status_code == 200
    assert resume_analysis_response.json()["analysis_status"] == "ready"

    match_response = client.post(
        f"/api/v1/jobs/{job_id}/match",
        json={"resume_id": resume_id},
    )

    assert match_response.status_code == 200
    body = match_response.json()
    assert body["matched_skills"] == ["Python", "FastAPI"]
    assert [gap["skill"] for gap in body["missing_skills"]] == ["Vector DB"]
    assert body["bonus_skills"] == []
    assert [gap["skill"] for gap in body["priority_skills"]] == ["Vector DB"]
    assert body["required_score"] == 53.3
    assert body["preferred_score"] == 0.0
    assert body["skill_coverage_score"] == 53.3
    assert "不能直接解释为值得投递或录用概率" in body["score_disclaimer"]


def test_match_returns_404_when_job_not_analyzed(application, client) -> None:
    _override_llm(application, FakeResumeLLM())
    job_id = _create_job(client)
    resume_id = _create_resume(client)

    response = client.post(
        f"/api/v1/jobs/{job_id}/match",
        json={"resume_id": resume_id},
    )

    assert response.status_code == 404


def test_resume_creation_succeeds_without_llm_configuration(client) -> None:
    response = client.post(
        "/api/v1/resumes",
        json={"title": "离线保存", "raw_text": "熟悉 Python。"},
    )

    assert response.status_code == 201
    assert response.json()["skills"] == []
    assert response.json()["analysis_status"] == "pending"


def test_resume_list_is_paginated_and_omits_raw_text(client) -> None:
    first_id = _create_resume(client)
    _create_resume(client)

    response = client.get("/api/v1/resumes?offset=1&limit=1")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == first_id
    assert "raw_text" not in response.json()[0]


def test_pending_resume_cannot_be_matched(application, client) -> None:
    _override_analysis(application, FakeAnalysisLLM())
    job_id = _create_job(client)
    assert client.post(f"/api/v1/jobs/{job_id}/analyze").status_code == 200
    resume_id = _create_resume(client)

    response = client.post(
        f"/api/v1/jobs/{job_id}/match",
        json={"resume_id": resume_id},
    )

    assert response.status_code == 409


def test_resume_rejects_blank_and_oversized_text(client) -> None:
    blank_response = client.post("/api/v1/resumes", json={"raw_text": "   "})
    oversized_response = client.post(
        "/api/v1/resumes",
        json={"raw_text": "x" * (MAX_RESUME_TEXT_CHARS + 1)},
    )

    assert blank_response.status_code == 422
    assert oversized_response.status_code == 422
