"""岗位垂直切片的 HTTP 测试。"""

from app.schemas.job import MAX_JOB_TEXT_CHARS


def test_job_crud_flow(client) -> None:
    create_response = client.post(
        "/api/v1/jobs",
        json={
            "company_name": "Example Co",
            "job_title": "RAG Intern",
            "city": "Singapore",
            "raw_text": "Build a retrieval service.",
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["status"] is None
    assert created["resume_id"] is None
    assert created["analysis_status"] == "pending"

    job_id = created["id"]
    update_response = client.patch(
        f"/api/v1/jobs/{job_id}",
        json={"city": "Remote"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["city"] == "Remote"

    bypass_response = client.patch(
        f"/api/v1/jobs/{job_id}",
        json={"status": "applied"},
    )
    assert bypass_response.status_code == 422

    list_response = client.get("/api/v1/jobs")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    delete_response = client.delete(f"/api/v1/jobs/{job_id}")
    assert delete_response.status_code == 204
    assert client.get(f"/api/v1/jobs/{job_id}").status_code == 404


def test_job_rejects_blank_and_oversized_text(client) -> None:
    blank_response = client.post(
        "/api/v1/jobs",
        json={"company_name": " ", "job_title": "实习生", "raw_text": "岗位描述"},
    )
    oversized_response = client.post(
        "/api/v1/jobs",
        json={
            "company_name": "示例公司",
            "job_title": "实习生",
            "raw_text": "x" * (MAX_JOB_TEXT_CHARS + 1),
        },
    )

    assert blank_response.status_code == 422
    assert oversized_response.status_code == 422
