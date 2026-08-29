"""Unit tests for the job-analysis service's evidence policy."""

from types import SimpleNamespace
from unittest.mock import Mock

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


def test_keeps_all_llm_evidence_without_strict_text_matching() -> None:
    result = JobRequirement(
        job_title="RAG Intern",
        evidence=[
            "python and fastapi experience",
            "This exact sentence is not in the raw text.",
        ],
    )

    actual = make_service(result).analyze_job(1)

    assert actual.evidence == result.evidence


def test_uses_raw_text_only_when_llm_returns_no_evidence() -> None:
    result = JobRequirement(job_title="RAG Intern")

    actual = make_service(result).analyze_job(1)

    assert actual.evidence == [
        "Python and FastAPI experience are preferred."
    ]
