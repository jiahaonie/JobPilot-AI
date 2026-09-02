"""岗位简历绑定与受控投递状态的集成测试。"""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_job_analysis_service, get_llm_client
from app.services.analysis import JobAnalysisService


class FakeResumeLLM:
    """返回固定简历技能的测试客户端。"""

    def complete_structured(self, *, prompt, response_model):
        return response_model.model_validate({"skills": ["Python"]})


class FakeJobLLM:
    """返回固定岗位要求的测试客户端。"""

    def complete_structured(self, *, prompt, response_model):
        return response_model.model_validate(
            {
                "job_title": "Backend Intern",
                "required_skills": ["Python"],
                "preferred_skills": [],
                "education": None,
                "internship_duration": None,
                "responsibilities": [],
                "evidence": ["Python"],
            }
        )


def _configure_analysis(application) -> None:
    application.dependency_overrides[get_llm_client] = lambda: FakeResumeLLM()

    def override_job_analysis(db: Session = Depends(get_db)) -> JobAnalysisService:
        return JobAnalysisService(db, FakeJobLLM())

    application.dependency_overrides[get_job_analysis_service] = override_job_analysis


def _create_job(client) -> int:
    response = client.post(
        "/api/v1/jobs",
        json={
            "company_name": "Example Co",
            "job_title": "Backend Intern",
            "raw_text": "Python",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_resume(client, title: str = "主简历") -> int:
    response = client.post(
        "/api/v1/resumes",
        json={"title": title, "raw_text": "Python"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_prepare_requires_bound_resume_and_both_analyses_ready(application, client) -> None:
    _configure_analysis(application)
    job_id = _create_job(client)
    resume_id = _create_resume(client)

    assert client.post(f"/api/v1/jobs/{job_id}/prepare").status_code == 409
    bind_response = client.put(
        f"/api/v1/jobs/{job_id}/resume",
        json={"resume_id": resume_id},
    )
    assert bind_response.status_code == 200
    assert bind_response.json()["resume_id"] == resume_id
    assert client.post(f"/api/v1/jobs/{job_id}/prepare").status_code == 409

    assert client.post(f"/api/v1/jobs/{job_id}/analyze").status_code == 200
    assert client.post(f"/api/v1/jobs/{job_id}/prepare").status_code == 409
    assert client.post(f"/api/v1/resumes/{resume_id}/analyze").status_code == 200

    prepare_response = client.post(f"/api/v1/jobs/{job_id}/prepare")
    assert prepare_response.status_code == 200
    assert prepare_response.json()["status"] == "preparing"


def test_job_status_uses_controlled_forward_transitions(application, client) -> None:
    _configure_analysis(application)
    job_id = _create_job(client)
    resume_id = _create_resume(client)
    client.put(f"/api/v1/jobs/{job_id}/resume", json={"resume_id": resume_id})
    client.post(f"/api/v1/jobs/{job_id}/analyze")
    client.post(f"/api/v1/resumes/{resume_id}/analyze")
    client.post(f"/api/v1/jobs/{job_id}/prepare")

    skipped = client.patch(
        f"/api/v1/jobs/{job_id}/status",
        json={"status": "interview"},
    )
    assert skipped.status_code == 409

    for expected in ("applied", "contacted", "interview"):
        response = client.patch(
            f"/api/v1/jobs/{job_id}/status",
            json={"status": expected},
        )
        assert response.status_code == 200
        assert response.json()["status"] == expected

    close_response = client.patch(
        f"/api/v1/jobs/{job_id}/status",
        json={"status": "closed"},
    )
    assert close_response.status_code == 200
    assert (
        client.patch(
            f"/api/v1/jobs/{job_id}/status",
            json={"status": "applied"},
        ).status_code
        == 409
    )


def test_active_stage_can_close_without_fake_intermediate_steps(application, client) -> None:
    _configure_analysis(application)
    job_id = _create_job(client)
    resume_id = _create_resume(client)
    client.put(f"/api/v1/jobs/{job_id}/resume", json={"resume_id": resume_id})
    client.post(f"/api/v1/jobs/{job_id}/analyze")
    client.post(f"/api/v1/resumes/{resume_id}/analyze")
    client.post(f"/api/v1/jobs/{job_id}/prepare")

    response = client.patch(
        f"/api/v1/jobs/{job_id}/status",
        json={"status": "closed"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "closed"


def test_resume_binding_can_change_only_before_preparation(application, client) -> None:
    _configure_analysis(application)
    job_id = _create_job(client)
    first_resume_id = _create_resume(client, "第一份")
    second_resume_id = _create_resume(client, "第二份")

    client.put(f"/api/v1/jobs/{job_id}/resume", json={"resume_id": first_resume_id})
    replacement = client.put(
        f"/api/v1/jobs/{job_id}/resume",
        json={"resume_id": second_resume_id},
    )
    assert replacement.status_code == 200
    assert replacement.json()["resume_id"] == second_resume_id

    client.post(f"/api/v1/jobs/{job_id}/analyze")
    client.post(f"/api/v1/resumes/{second_resume_id}/analyze")
    client.post(f"/api/v1/jobs/{job_id}/prepare")

    assert (
        client.put(
            f"/api/v1/jobs/{job_id}/resume",
            json={"resume_id": first_resume_id},
        ).status_code
        == 409
    )
    assert client.delete(f"/api/v1/jobs/{job_id}/resume").status_code == 409


def test_bound_resume_is_protected_and_job_delete_cascades_binding(client) -> None:
    job_id = _create_job(client)
    resume_id = _create_resume(client)
    client.put(f"/api/v1/jobs/{job_id}/resume", json={"resume_id": resume_id})

    assert client.delete(f"/api/v1/resumes/{resume_id}").status_code == 409
    assert client.delete(f"/api/v1/jobs/{job_id}").status_code == 204
    assert client.delete(f"/api/v1/resumes/{resume_id}").status_code == 204


def test_resume_can_be_deleted_after_unbinding_before_preparation(client) -> None:
    job_id = _create_job(client)
    resume_id = _create_resume(client)
    client.put(f"/api/v1/jobs/{job_id}/resume", json={"resume_id": resume_id})

    assert client.delete(f"/api/v1/jobs/{job_id}/resume").status_code == 204
    assert client.delete(f"/api/v1/resumes/{resume_id}").status_code == 204
