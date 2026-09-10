"""岗位分析用例：通过 LLM 将原始 JD 转为结构化要求。"""

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import AnalysisPersistenceError, LLMAnalysisError
from app.llm.client import StructuredLLMClient
from app.llm.exceptions import LLMError
from app.llm.prompts import build_job_requirement_prompt
from app.models.enums import JobAnalysisStatus
from app.models.job import Job
from app.models.job_analysis import JobAnalysis
from app.models.job_requirement import JobRequirementRow
from app.repositories.job_requirement import JobRequirementRepository
from app.schemas.requirements import JobRequirement
from app.services.job import JobService
from app.services.skill_normalization import SkillNormalizer

logger = logging.getLogger(__name__)


class JobAnalysisService:
    """协调 LLM 分析，并将服务商细节隔离在路由之外。"""

    def __init__(
        self,
        session: Session,
        client: StructuredLLMClient,
    ) -> None:
        self.session = session
        self.client = client
        self.job_service = JobService(session)
        self.requirement_repository = JobRequirementRepository(session)

    def analyze_job(self, job_id: int) -> JobRequirement:
        """从已保存的岗位描述中提取结构化要求。"""
        job = self.job_service.get(job_id)
        analysis = self._ensure_analysis(job)
        analysis.status = JobAnalysisStatus.ANALYZING
        analysis.error_message = None
        try:
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            raise AnalysisPersistenceError("Job analysis state could not be saved") from exc

        prompt = build_job_requirement_prompt(
            job.raw_text,
            job_title=job.job_title,
        )
        try:
            result = self.client.complete_structured(
                prompt=prompt,
                response_model=JobRequirement,
            )
        except LLMError as exc:
            self._record_failure(job_id, str(exc))
            raise LLMAnalysisError(f"Job analysis failed: {exc}") from exc
        except Exception as exc:
            self._record_failure(job_id, "Unexpected analysis failure")
            raise LLMAnalysisError("Job analysis failed unexpectedly") from exc
        try:
            result = _prepare_v2_result(result, job.raw_text)
        except ValueError as exc:
            self._record_failure(job_id, str(exc))
            raise LLMAnalysisError(f"Job analysis produced invalid requirements: {exc}") from exc
        self._persist(job, result)
        return result

    def _persist(self, job: Job, result: JobRequirement) -> None:
        """保存最新分析，写入失败时明确报告错误。"""
        row = JobRequirementRow(
            job_id=job.id,
            job_title=result.job_title,
            extraction_version=result.extraction_version,
            skill_requirements=[item.model_dump(mode="json") for item in result.skill_requirements],
            unscored_requirements=[
                item.model_dump(mode="json") for item in result.unscored_requirements
            ],
            required_skills=result.required_skills,
            preferred_skills=result.preferred_skills,
            education=result.education,
            internship_duration=result.internship_duration,
            responsibilities=result.responsibilities,
            evidence=result.evidence,
        )
        try:
            self.requirement_repository.upsert(row)
            analysis = self._ensure_analysis(job)
            analysis.status = JobAnalysisStatus.READY
            analysis.error_message = None
            analysis.analyzed_at = datetime.now(UTC)
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            logger.exception("Failed to persist job requirements for job %s", job.id)
            try:
                self._record_failure(job.id, "Analysis result could not be saved")
            except AnalysisPersistenceError:
                logger.exception("Failed to persist failure state for job %s", job.id)
            raise AnalysisPersistenceError("Job analysis result could not be saved") from exc

    @staticmethod
    def _ensure_analysis(job: Job) -> JobAnalysis:
        """返回岗位分析记录，并为旧对象补建待处理记录。"""
        analysis = job.analysis
        if analysis is None:
            analysis = JobAnalysis(job_id=job.id)
            job.analysis = analysis
        return analysis

    def _record_failure(self, job_id: int, message: str) -> None:
        """在当前事务回滚后保存岗位分析失败状态。"""
        try:
            job = self.job_service.get(job_id)
            analysis = self._ensure_analysis(job)
            analysis.status = JobAnalysisStatus.FAILED
            analysis.error_message = message
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            raise AnalysisPersistenceError("Job analysis failure state could not be saved") from exc


def _grounded_evidence(evidence: list[str], raw_text: str) -> list[str]:
    """仅保留可在原始 JD 中定位的证据片段。"""
    normalized_raw_text = " ".join(raw_text.casefold().split())
    return [
        excerpt
        for excerpt in evidence
        if (normalized_excerpt := " ".join(excerpt.casefold().split()))
        and normalized_excerpt in normalized_raw_text
    ]


_FORBIDDEN_OPTION_MARKERS = ("\n", "\r", "/", "，", ",", "；", ";", "。", "！", "？")


def _prepare_v2_result(result: JobRequirement, raw_text: str) -> JobRequirement:
    """校验 V2 原子技能和证据，并生成只用于兼容的扁平技能字段。"""
    if result.extraction_version != "job-requirements-v2":
        raise ValueError("extraction_version must be job-requirements-v2")

    normalizer = SkillNormalizer()
    required: list[str] = []
    preferred: list[str] = []
    all_evidence: list[str] = []
    for requirement in result.skill_requirements:
        if not _excerpt_in_text(requirement.evidence, raw_text):
            raise ValueError(
                f"skill requirement evidence is not present in JD: {requirement.label}"
            )
        seen: set[str] = set()
        for option in requirement.options:
            if len(option) > 80 or any(marker in option for marker in _FORBIDDEN_OPTION_MARKERS):
                raise ValueError(f"skill option is not atomic: {option}")
            if not normalizer.contains_evidence(requirement.evidence, option):
                raise ValueError(f"skill option is not supported by evidence: {option}")
            canonical = normalizer.canonical_name(option)
            if not canonical or canonical in seen:
                raise ValueError(f"skill option is empty or duplicated: {option}")
            seen.add(canonical)
        target = required if requirement.importance == "required" else preferred
        target.extend(requirement.options)
        all_evidence.append(requirement.evidence)

    for requirement in result.unscored_requirements:
        if not _excerpt_in_text(requirement.evidence, raw_text):
            raise ValueError("unscored requirement evidence is not present in JD")
        all_evidence.append(requirement.evidence)

    result.required_skills = list(dict.fromkeys(required))
    result.preferred_skills = list(dict.fromkeys(preferred))
    result.evidence = list(dict.fromkeys(_grounded_evidence(all_evidence, raw_text)))
    return result


def _excerpt_in_text(excerpt: str, raw_text: str) -> bool:
    normalized_excerpt = " ".join(excerpt.casefold().split())
    normalized_raw = " ".join(raw_text.casefold().split())
    return bool(normalized_excerpt) and normalized_excerpt in normalized_raw
