"""不可变持久化匹配报告的集成测试。"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.enums import ResumeAnalysisStatus
from app.models.job_requirement import JobRequirementRow
from app.models.match_report import MatchReportRow
from app.models.resume import Resume


def seed_match_sources(application: FastAPI, client: TestClient) -> tuple[int, int]:
    """不调用 LLM，创建一个已分析岗位和一份就绪简历。"""
    job_response = client.post(
        "/api/v1/jobs",
        json={
            "company_name": "Example Co",
            "job_title": "RAG Intern",
            "raw_text": "Python, Vector Database and FastAPI are useful.",
        },
    )
    resume_response = client.post(
        "/api/v1/resumes",
        json={"title": "AI Resume", "raw_text": "Python and Vector DB projects."},
    )
    assert job_response.status_code == 201
    assert resume_response.status_code == 201
    job_id = job_response.json()["id"]
    resume_id = resume_response.json()["id"]

    database = application.state.database
    with database.session() as session:
        resume = session.get(Resume, resume_id)
        assert resume is not None
        resume.skills = ["Python", "Vector DB"]
        assert resume.analysis is not None
        resume.analysis.status = ResumeAnalysisStatus.READY
        session.add(
            JobRequirementRow(
                job_id=job_id,
                job_title="RAG Intern",
                required_skills=["Python", "向量数据库"],
                preferred_skills=["FastAPI"],
                responsibilities=["Build retrieval services"],
                evidence=["Python, Vector Database and FastAPI are useful."],
            )
        )
        session.commit()
    return job_id, resume_id


def test_create_read_list_and_keep_match_report_snapshot(
    application: FastAPI,
    client: TestClient,
) -> None:
    job_id, resume_id = seed_match_sources(application, client)

    create_response = client.post(
        f"/api/v1/jobs/{job_id}/match-reports",
        json={"resume_id": resume_id},
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["skill_coverage_score"] == 80.0
    assert created["required_score"] == 80.0
    assert created["preferred_score"] == 0.0
    assert created["matched_skills"] == ["Python", "向量数据库"]
    assert created["required_skills_snapshot"] == ["Python", "向量数据库"]
    assert created["resume_skills_snapshot"] == ["Python", "Vector DB"]
    assert created["scoring_version"] == "skill-coverage-v1"
    assert "录用概率" in created["score_disclaimer"]

    report_id = created["id"]
    database = application.state.database
    with database.session() as session:
        resume = session.get(Resume, resume_id)
        requirement = session.scalar(
            select(JobRequirementRow).where(JobRequirementRow.job_id == job_id)
        )
        assert resume is not None
        assert requirement is not None
        resume.skills = ["Go"]
        requirement.required_skills = ["Go"]
        session.commit()

    detail_response = client.get(f"/api/v1/match-reports/{report_id}")
    list_response = client.get(
        "/api/v1/match-reports",
        params={"job_id": job_id, "resume_id": resume_id},
    )

    assert detail_response.status_code == 200
    assert detail_response.json() == created
    assert list_response.status_code == 200
    assert list_response.json() == [created]


@pytest.mark.parametrize("deleted_source", ["job", "resume"])
def test_deleting_source_cascades_to_match_report(
    deleted_source: str,
    application: FastAPI,
    client: TestClient,
) -> None:
    job_id, resume_id = seed_match_sources(application, client)
    create_response = client.post(
        f"/api/v1/jobs/{job_id}/match-reports",
        json={"resume_id": resume_id},
    )
    assert create_response.status_code == 201
    report_id = create_response.json()["id"]

    if deleted_source == "job":
        delete_response = client.delete(f"/api/v1/jobs/{job_id}")
    else:
        delete_response = client.delete(f"/api/v1/resumes/{resume_id}")

    assert delete_response.status_code == 204
    assert client.get(f"/api/v1/match-reports/{report_id}").status_code == 404
    with application.state.database.session() as session:
        assert session.get(MatchReportRow, report_id) is None
        if deleted_source == "job":
            requirement = session.scalar(
                select(JobRequirementRow).where(JobRequirementRow.job_id == job_id)
            )
            assert requirement is None
