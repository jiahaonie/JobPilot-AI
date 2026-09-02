"""解耦简历存储与 LLM 分析的单元测试。"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.exceptions import LLMAnalysisError
from app.llm.exceptions import LLMNotConfiguredError
from app.models.base import Base
from app.models.enums import ResumeAnalysisStatus
from app.models.resume import Resume
from app.schemas.resume import ResumeCreate
from app.services.resume import ResumeAnalysisService, ResumeService


class FakeLLMClient:
    def __init__(self, skills=None, fail: bool = False, unexpected: bool = False) -> None:
        self.skills = skills or []
        self.fail = fail
        self.unexpected = unexpected

    def complete_structured(self, *, prompt, response_model):
        if self.fail:
            raise LLMNotConfiguredError("boom")
        if self.unexpected:
            raise RuntimeError("provider bug")
        return response_model.model_validate({"skills": self.skills})


@pytest.fixture
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    yield session_factory()
    engine.dispose()


def test_create_persists_before_analysis(session) -> None:
    service = ResumeService(session)

    resume = service.create(ResumeCreate(title="简历", raw_text="熟悉 Python 和 FastAPI。"))

    assert resume.skills == []
    assert resume.analysis_status == ResumeAnalysisStatus.PENDING
    assert resume.id is not None
    assert session.get(Resume, resume.id) is not None


def test_create_derives_title_when_omitted(session) -> None:
    service = ResumeService(session)

    resume = service.create(ResumeCreate(raw_text="熟悉 Python 开发。"))

    assert resume.title == "熟悉 Python 开发。"


def test_analysis_updates_saved_resume(session) -> None:
    resume = ResumeService(session).create(
        ResumeCreate(title="简历", raw_text="熟悉 Python 和 FastAPI。")
    )

    analyzed = ResumeAnalysisService(
        session,
        FakeLLMClient(skills=["Python", "FastAPI"]),
    ).analyze(resume.id)

    assert analyzed.skills == ["Python", "FastAPI"]
    assert analyzed.analysis_status == ResumeAnalysisStatus.READY
    assert analyzed.analyzed_at is not None


def test_analysis_failure_keeps_resume_and_records_failure(session) -> None:
    resume = ResumeService(session).create(ResumeCreate(title="x", raw_text="y"))
    service = ResumeAnalysisService(session, FakeLLMClient(fail=True))

    with pytest.raises(LLMAnalysisError):
        service.analyze(resume.id)

    persisted = session.get(Resume, resume.id)
    assert persisted is not None
    assert persisted.analysis_status == ResumeAnalysisStatus.FAILED
    assert persisted.analysis_error == "boom"


def test_unexpected_analysis_failure_does_not_leave_analyzing_state(session) -> None:
    resume = ResumeService(session).create(ResumeCreate(title="x", raw_text="y"))
    service = ResumeAnalysisService(session, FakeLLMClient(unexpected=True))

    with pytest.raises(LLMAnalysisError):
        service.analyze(resume.id)

    persisted = session.get(Resume, resume.id)
    assert persisted.analysis_status == ResumeAnalysisStatus.FAILED
    assert persisted.analysis_error == "Unexpected analysis failure"
