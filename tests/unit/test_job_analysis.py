"""岗位分析服务证据策略的单元测试。"""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.core.exceptions import AnalysisPersistenceError, LLMAnalysisError
from app.models.enums import JobAnalysisStatus
from app.models.job_analysis import JobAnalysis
from app.schemas.requirements import JobRequirement, SkillRequirement, UnscoredRequirement
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
        id=1,
        raw_text="Python and FastAPI experience are preferred.",
        job_title="RAG Intern",
        analysis=JobAnalysis(status=JobAnalysisStatus.PENDING),
    )
    return service


def test_discards_evidence_that_cannot_be_located_in_raw_text() -> None:
    result = JobRequirement(
        job_title="RAG Intern",
        skill_requirements=[
            SkillRequirement(
                label="Python",
                importance="required",
                match_mode="all",
                options=["Python"],
                evidence="python and fastapi experience",
            )
        ],
        evidence=["This exact sentence is not in the raw text."],
    )

    actual = make_service(result).analyze_job(1)

    assert actual.evidence == ["python and fastapi experience"]


def test_does_not_use_whole_jd_as_fallback_evidence() -> None:
    result = JobRequirement(job_title="RAG Intern")

    actual = make_service(result).analyze_job(1)

    assert actual.evidence == []


def test_rejects_non_atomic_skill_option_and_records_failure() -> None:
    result = JobRequirement(
        job_title="RAG Intern",
        skill_requirements=[
            SkillRequirement(
                label="语言",
                importance="required",
                match_mode="any",
                options=["Python/TypeScript"],
                evidence="Python and FastAPI experience are preferred.",
            )
        ],
    )
    service = make_service(result)

    with pytest.raises(LLMAnalysisError, match="not atomic"):
        service.analyze_job(1)

    assert service.job_service.get.return_value.analysis.status == JobAnalysisStatus.FAILED


def test_unknown_unscored_category_falls_back_to_other() -> None:
    requirement = UnscoredRequirement.model_validate(
        {
            "category": "preferred",
            "text": "有开源项目经验者优先",
            "evidence": "有开源项目经验者优先",
        }
    )

    assert requirement.category == "other"


def test_persistence_failure_is_reported_instead_of_returning_success() -> None:
    result = JobRequirement(job_title="RAG Intern", evidence=["Python"])
    service = make_service(result)
    service.session.commit.side_effect = RuntimeError("database unavailable")

    with pytest.raises(AnalysisPersistenceError):
        service.analyze_job(1)

    service.session.rollback.assert_called_once_with()
