"""Integration tests for the job-requirements endpoint with a mocked client."""

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_job_analysis_service
from app.llm.exceptions import StructuredOutputError
from app.services.analysis import JobAnalysisService


class FakeLLMClient:
    """In-memory provider adapter used to drive integration tests."""

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail

    def complete_structured(self, *, prompt, response_model):
        if self.fail:
            raise StructuredOutputError("fake provider returned invalid output")
        return response_model.model_validate(
            {
                "job_title": "RAG Intern",
                "required_skills": ["Python"],
                "preferred_skills": ["FastAPI"],
                "education": None,
                "internship_duration": None,
                "responsibilities": ["Build retrieval service"],
                "evidence": ["Build a retrieval service"],
            }
        )


def override_analysis_dependency(
    application: FastAPI,
    client: FakeLLMClient,
) -> None:
    """Point the app's analysis dependency at a fake client."""

    def override_service(db: Session = Depends(get_db)) -> JobAnalysisService:
        return JobAnalysisService(db, client)

    application.dependency_overrides[get_job_analysis_service] = override_service


def create_job(client: TestClient) -> int:
    response = client.post(
        "/api/v1/jobs",
        json={
            "company_name": "Example Co",
            "job_title": "RAG Intern",
            "city": "Singapore",
            "raw_text": "Build a retrieval service.",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_job_requirements_endpoint_returns_structured_output(
    application,
    client,
) -> None:
    override_analysis_dependency(application, FakeLLMClient())
    job_id = create_job(client)

    response = client.get(f"/api/v1/jobs/{job_id}/requirements")

    assert response.status_code == 200
    body = response.json()
    assert body["job_title"] == "RAG Intern"
    assert body["required_skills"] == ["Python"]
    assert body["evidence"] == ["Build a retrieval service"]


def test_job_requirements_returns_503_when_analysis_fails(
    application,
    client,
) -> None:
    override_analysis_dependency(application, FakeLLMClient(fail=True))
    job_id = create_job(client)

    response = client.get(f"/api/v1/jobs/{job_id}/requirements")

    assert response.status_code == 503


def test_job_requirements_returns_404_for_missing_job(application, client) -> None:
    override_analysis_dependency(application, FakeLLMClient())

    response = client.get("/api/v1/jobs/999999/requirements")

    assert response.status_code == 404
