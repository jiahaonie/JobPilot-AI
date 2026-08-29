"""Unit tests for the resume service with a mocked LLM client."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.exceptions import LLMAnalysisError
from app.models.base import Base
from app.models.resume import Resume
from app.schemas.resume import ResumeCreate
from app.services.resume import ResumeService


class FakeLLMClient:
    def __init__(self, skills=None, fail: bool = False) -> None:
        self.skills = skills or []
        self.fail = fail

    def complete_structured(self, *, prompt, response_model):
        if self.fail:
            raise LLMAnalysisError("boom")
        return response_model.model_validate({"skills": self.skills})


@pytest.fixture
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    yield session_factory()
    engine.dispose()


def test_create_extracts_skills_and_persists(session) -> None:
    service = ResumeService(session, FakeLLMClient(skills=["Python", "FastAPI"]))

    resume = service.create(
        ResumeCreate(title="简历", raw_text="熟悉 Python 和 FastAPI。")
    )

    assert resume.skills == ["Python", "FastAPI"]
    assert resume.id is not None
    assert session.get(Resume, resume.id) is not None


def test_create_derives_title_when_omitted(session) -> None:
    service = ResumeService(session, FakeLLMClient(skills=["Python"]))

    resume = service.create(ResumeCreate(raw_text="熟悉 Python 开发。"))

    assert resume.title == "熟悉 Python 开发。"


def test_extraction_failure_fails_creation(session) -> None:
    service = ResumeService(session, FakeLLMClient(fail=True))

    with pytest.raises(LLMAnalysisError):
        service.create(ResumeCreate(title="x", raw_text="y"))
