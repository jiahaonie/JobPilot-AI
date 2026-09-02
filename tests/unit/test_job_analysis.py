"""岗位分析服务证据策略的单元测试。"""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.core.exceptions import AnalysisPersistenceError
from app.schemas.requirements import JobRequirement
from app.services.analysis import JobAnalysisService


class FakeLLMClient:
    def __init__(self, result: JobRequirement) -> None:
        self.result = result

    def complete_structured(self, *, prompt, response_model) -> JobRequirement:
        return self.result


def make_service(result: JobRequirement) -> JobAnalysisService:
    service = JobAnalysisService(Mock(), FakeLLMClient(result))
    service.job_service = Mock()
    service.job_service.get.return_value = SimpleNamespace(
        raw_text="Python and FastAPI experience are preferred.",
        job_title="RAG Intern",
    )
    return service


def test_discards_evidence_that_cannot_be_located_in_raw_text() -> None:
    result = JobRequirement(
        job_title="RAG Intern",
        evidence=[
            "python and fastapi experience",
            "This exact sentence is not in the raw text.",
        ],
    )

    actual = make_service(result).analyze_job(1)

    assert actual.evidence == ["python and fastapi experience"]


def test_uses_raw_text_only_when_llm_returns_no_evidence() -> None:
    result = JobRequirement(job_title="RAG Intern")

    actual = make_service(result).analyze_job(1)

    assert actual.evidence == ["Python and FastAPI experience are preferred."]


def test_persistence_failure_is_reported_instead_of_returning_success() -> None:
    result = JobRequirement(job_title="RAG Intern", evidence=["Python"])
    service = make_service(result)
    service.session.commit.side_effect = RuntimeError("database unavailable")

    with pytest.raises(AnalysisPersistenceError):
        service.analyze_job(1)

    service.session.rollback.assert_called_once_with()
