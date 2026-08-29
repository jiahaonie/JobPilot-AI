"""Unit tests for the pure-logic resume-to-job matcher."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.exceptions import JobRequirementNotFoundError, ResourceNotFoundError
from app.models.base import Base
from app.models.job_requirement import JobRequirementRow
from app.models.resume import Resume
from app.services.matching import MatchService


@pytest.fixture
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    yield session_factory()
    engine.dispose()


def make_requirement(session, job_id=1, required=None, preferred=None, evidence=None):
    row = JobRequirementRow(
        job_id=job_id,
        job_title="RAG Intern",
        required_skills=required or ["Python", "FastAPI", "Vector DB"],
        preferred_skills=preferred or ["NLP"],
        evidence=evidence or [
            "Proficient in Python.",
            "Experience with FastAPI.",
            "Knowledge of Vector DB.",
        ],
    )
    session.add(row)
    session.commit()
    return row


def make_resume(session, skills, resume_id=1):
    resume = Resume(
        id=resume_id,
        title="Resume",
        raw_text="x",
        skills=skills,
    )
    session.add(resume)
    session.commit()
    return resume


def test_matched_and_missing_skills(session) -> None:
    make_requirement(session)
    make_resume(session, ["Python"])

    report = MatchService(session).match(job_id=1, resume_id=1)

    assert report.matched_skills == ["Python"]
    assert [gap.skill for gap in report.missing_skills] == ["FastAPI", "Vector DB"]
    assert [gap.skill for gap in report.priority_skills] == ["FastAPI", "Vector DB"]


def test_matching_is_case_and_space_insensitive(session) -> None:
    make_requirement(session)
    make_resume(session, ["fastapi"])

    report = MatchService(session).match(job_id=1, resume_id=1)

    assert report.matched_skills == ["FastAPI"]


def test_bonus_skills_reports_preferred_satisfied(session) -> None:
    make_requirement(session)
    make_resume(session, ["NLP", "Vector DB"])

    report = MatchService(session).match(job_id=1, resume_id=1)

    assert report.bonus_skills == ["NLP"]
    assert report.matched_skills == ["Vector DB"]


def test_all_satisfied_gives_empty_missing(session) -> None:
    make_requirement(session)
    make_resume(session, ["Python", "FastAPI", "Vector DB"])

    report = MatchService(session).match(job_id=1, resume_id=1)

    assert report.missing_skills == []
    assert report.matched_skills == ["Python", "FastAPI", "Vector DB"]


def test_priority_skills_limited_to_three(session) -> None:
    make_requirement(session, required=[f"Skill {i}" for i in range(5)])
    make_resume(session, [])

    report = MatchService(session).match(job_id=1, resume_id=1)

    assert [gap.skill for gap in report.priority_skills] == [
        "Skill 0",
        "Skill 1",
        "Skill 2",
    ]


def test_missing_job_requirement_raises(session) -> None:
    make_resume(session, ["Python"])

    with pytest.raises(JobRequirementNotFoundError):
        MatchService(session).match(job_id=1, resume_id=1)


def test_missing_resume_raises(session) -> None:
    make_requirement(session)

    with pytest.raises(ResourceNotFoundError):
        MatchService(session).match(job_id=1, resume_id=999)
