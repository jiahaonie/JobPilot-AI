"""Integration tests for the resume + match HTTP flow."""

from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_db,
    get_job_analysis_service,
    get_llm_client,
)
from app.services.analysis import JobAnalysisService


class FakeResumeLLM:
    def complete_structured(self, *, prompt, response_model):
        return response_model.model_validate({"skills": ["Python", "FastAPI"]})


class FakeAnalysisLLM:
    def complete_structured(self, *, prompt, response_model):
        return response_model.model_validate(
            {
                "job_title": "RAG Intern",
                "required_skills": ["Python", "FastAPI", "Vector DB"],
                "preferred_skills": ["NLP"],
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
            "raw_text": "Proficient in Python and FastAPI. Knowledge of Vector DB.",
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
    return response.json()["id"]


def test_resume_creation_and_match_flow(application, client) -> None:
    _override_llm(application, FakeResumeLLM())
    _override_analysis(application, FakeAnalysisLLM())

    job_id = _create_job(client)
    analyze_response = client.get(f"/api/v1/jobs/{job_id}/requirements")
    assert analyze_response.status_code == 200
    resume_id = _create_resume(client)

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


def test_match_returns_404_when_job_not_analyzed(application, client) -> None:
    _override_llm(application, FakeResumeLLM())
    job_id = _create_job(client)
    resume_id = _create_resume(client)

    response = client.post(
        f"/api/v1/jobs/{job_id}/match",
        json={"resume_id": resume_id},
    )

    assert response.status_code == 404
