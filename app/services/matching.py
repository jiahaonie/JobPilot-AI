"""Resume-to-job matching: pure logic, no LLM involved."""

from sqlalchemy.orm import Session

from app.core.exceptions import (
    JobRequirementNotFoundError,
    ResourceNotFoundError,
    ResumeAnalysisNotReadyError,
)
from app.models.enums import ResumeAnalysisStatus
from app.repositories.job_requirement import JobRequirementRepository
from app.repositories.resume import ResumeRepository
from app.schemas.matching import MatchReport, SkillGap
from app.services.skill_normalization import SkillNormalizer

PRIORITY_LIMIT = 3
REQUIRED_WEIGHT = 80
PREFERRED_WEIGHT = 20


class MatchService:
    """Compare a resume's skills against one job's structured requirements."""

    def __init__(
        self,
        session: Session,
        normalizer: SkillNormalizer | None = None,
    ) -> None:
        self.session = session
        self.job_requirement_repository = JobRequirementRepository(session)
        self.resume_repository = ResumeRepository(session)
        self.normalizer = normalizer or SkillNormalizer()

    def match(self, job_id: int, resume_id: int) -> MatchReport:
        """Build an explained skill report for one resume against one job."""

        requirement = self.job_requirement_repository.get_by_job(job_id)
        if requirement is None:
            raise JobRequirementNotFoundError(
                f"Job {job_id} has not been analyzed yet"
            )
        resume = self.resume_repository.get(resume_id)
        if resume is None:
            raise ResourceNotFoundError(f"Resume {resume_id} was not found")
        if resume.analysis_status != ResumeAnalysisStatus.READY:
            raise ResumeAnalysisNotReadyError(
                f"Resume {resume_id} analysis is {resume.analysis_status}"
            )

        resume_normalized = {
            self.normalizer.canonical_name(skill) for skill in resume.skills
        }
        evidence_by_skill = self._evidence_lookup(requirement.evidence)

        matched_skills: list[str] = []
        for skill in requirement.required_skills:
            if self.normalizer.canonical_name(skill) in resume_normalized:
                matched_skills.append(skill)

        bonus_skills: list[str] = []
        for skill in requirement.preferred_skills:
            if self.normalizer.canonical_name(skill) in resume_normalized:
                bonus_skills.append(skill)

        missing_skills: list[SkillGap] = []
        for skill in requirement.required_skills:
            if self.normalizer.canonical_name(skill) not in resume_normalized:
                missing_skills.append(
                    SkillGap(skill=skill, evidence=evidence_by_skill(skill))
                )

        priority_skills = missing_skills[:PRIORITY_LIMIT]
        skill_coverage_score, required_score, preferred_score = self._scores(
            matched_required=len(matched_skills),
            total_required=len(requirement.required_skills),
            matched_preferred=len(bonus_skills),
            total_preferred=len(requirement.preferred_skills),
        )
        return MatchReport(
            skill_coverage_score=skill_coverage_score,
            required_score=required_score,
            preferred_score=preferred_score,
            matched_skills=matched_skills,
            bonus_skills=bonus_skills,
            missing_skills=missing_skills,
            priority_skills=priority_skills,
        )

    def _evidence_lookup(self, evidence: list[str]):
        """Return a function mapping a skill to its supporting job text."""

        def find(skill: str) -> str | None:
            accepted_terms = self.normalizer.evidence_terms(skill)
            for excerpt in evidence:
                normalized_excerpt = self.normalizer.normalize_evidence(excerpt)
                if any(term in normalized_excerpt for term in accepted_terms):
                    return excerpt
            return None

        return find

    @staticmethod
    def _scores(
        *,
        matched_required: int,
        total_required: int,
        matched_preferred: int,
        total_preferred: int,
    ) -> tuple[float | None, float | None, float | None]:
        """Return deterministic weighted skill-coverage score components."""

        if total_required == 0:
            return None, None, None

        required_coverage = matched_required / total_required
        if total_preferred == 0:
            required_score = round(required_coverage * 100, 1)
            return required_score, required_score, None

        required_score = round(required_coverage * REQUIRED_WEIGHT, 1)
        preferred_score = round(
            matched_preferred / total_preferred * PREFERRED_WEIGHT,
            1,
        )
        skill_coverage_score = round(required_score + preferred_score, 1)
        return skill_coverage_score, required_score, preferred_score
