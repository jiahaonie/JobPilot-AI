"""使用模拟客户端测试岗位要求端点。"""

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_job_analysis_service
from app.llm.exceptions import StructuredOutputError
from app.services.analysis import JobAnalysisService


class FakeLLMClient:
    """用于驱动集成测试的内存服务商适配器。"""

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls = 0

    def complete_structured(self, *, prompt, response_model):
        self.calls += 1
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
    """将应用的分析依赖指向模拟客户端。"""

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


def test_analyze_then_get_requirements_without_reanalyzing(
    application,
    client,
) -> None:
    fake_client = FakeLLMClient()
    override_analysis_dependency(application, fake_client)
    job_id = create_job(client)

    analyze_response = client.post(f"/api/v1/jobs/{job_id}/analyze")
    response = client.get(f"/api/v1/jobs/{job_id}/requirements")

    assert analyze_response.status_code == 200
    assert response.status_code == 200
    body = response.json()
    assert body["job_title"] == "RAG Intern"
    assert body["required_skills"] == ["Python"]
    assert body["evidence"] == ["Build a retrieval service"]
    assert fake_client.calls == 1


def test_job_analyze_returns_503_when_analysis_fails(
    application,
    client,
) -> None:
    override_analysis_dependency(application, FakeLLMClient(fail=True))
    job_id = create_job(client)

    response = client.post(f"/api/v1/jobs/{job_id}/analyze")

    assert response.status_code == 503


def test_job_requirements_returns_404_before_analysis(client) -> None:
    job_id = create_job(client)

    response = client.get(f"/api/v1/jobs/{job_id}/requirements")

    assert response.status_code == 404


def test_updating_analysis_fields_invalidates_stored_requirements(
    application,
    client,
) -> None:
    override_analysis_dependency(application, FakeLLMClient())
    job_id = create_job(client)
    assert client.post(f"/api/v1/jobs/{job_id}/analyze").status_code == 200

    update_response = client.patch(
        f"/api/v1/jobs/{job_id}",
        json={"raw_text": "Updated job description."},
    )

    assert update_response.status_code == 200
    assert update_response.json()["status"] == "pending_analysis"
    assert client.get(f"/api/v1/jobs/{job_id}/requirements").status_code == 404


def test_updating_unrelated_fields_keeps_stored_requirements(application, client) -> None:
    override_analysis_dependency(application, FakeLLMClient())
    job_id = create_job(client)
    assert client.post(f"/api/v1/jobs/{job_id}/analyze").status_code == 200

    update_response = client.patch(
        f"/api/v1/jobs/{job_id}",
        json={"city": "Remote", "status": "applied"},
    )

    assert update_response.status_code == 200
    assert update_response.json()["status"] == "applied"
    assert client.get(f"/api/v1/jobs/{job_id}/requirements").status_code == 200
