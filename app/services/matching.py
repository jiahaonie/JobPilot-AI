"""简历与岗位的纯逻辑匹配，不调用 LLM。"""

from collections.abc import Callable

from sqlalchemy.orm import Session

from app.core.exceptions import (
    JobRequirementNotFoundError,
    ResourceNotFoundError,
    ResumeAnalysisNotReadyError,
)
from app.models.enums import ResumeAnalysisStatus
from app.repositories.job_requirement import JobRequirementRepository
from app.repositories.resume import ResumeRepository
from app.schemas.matching import (
    MatchReport,
    RequirementMatch,
    SkillGap,
    SkillOptionMatch,
)
from app.schemas.requirements import SkillRequirement
from app.services.skill_normalization import SkillNormalizer

PRIORITY_LIMIT = 3
REQUIRED_WEIGHT = 80
PREFERRED_WEIGHT = 20


class MatchService:
    """根据岗位结构化要求匹配简历技能。"""

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
        """生成一份可解释的简历岗位技能匹配报告。"""
        requirement = self.job_requirement_repository.get_by_job(job_id)
        if requirement is None:
            raise JobRequirementNotFoundError(f"Job {job_id} has not been analyzed yet")
        resume = self.resume_repository.get(resume_id)
        if resume is None:
            raise ResourceNotFoundError(f"Resume {resume_id} was not found")
        if resume.analysis_status != ResumeAnalysisStatus.READY:
            raise ResumeAnalysisNotReadyError(
                f"Resume {resume_id} analysis is {resume.analysis_status}"
            )

        if (
            requirement.extraction_version == "job-requirements-v2"
            and requirement.skill_requirements is not None
        ):
            return self._match_v2(requirement.skill_requirements, resume.skills, resume.raw_text)
        return self._match_v1(requirement, resume.skills)

    def _match_v2(
        self,
        stored_requirements: list[dict],
        resume_skills: list[str],
        resume_text: str,
    ) -> MatchReport:
        """按要求组计算 V2 覆盖状态、组级分数和双侧证据。"""
        resume_index: dict[str, str] = {}
        for skill in resume_skills:
            resume_index.setdefault(self.normalizer.canonical_name(skill), skill)

        matches: list[RequirementMatch] = []
        required_coverages: list[float] = []
        preferred_coverages: list[float] = []
        matched_skills: list[str] = []
        bonus_skills: list[str] = []
        missing_skills: list[SkillGap] = []

        for stored in stored_requirements:
            requirement = SkillRequirement.model_validate(stored)
            option_matches = [
                self._match_option(option, resume_index, resume_text)
                for option in requirement.options
            ]
            matched_count = sum(
                option.matched_resume_skill is not None for option in option_matches
            )
            if requirement.match_mode == "any":
                coverage = 1.0 if matched_count else 0.0
                status = "covered" if matched_count else "missing"
            else:
                coverage = matched_count / len(option_matches)
                status = (
                    "covered"
                    if matched_count == len(option_matches)
                    else "partial"
                    if matched_count
                    else "missing"
                )

            target_coverages = (
                required_coverages if requirement.importance == "required" else preferred_coverages
            )
            target_coverages.append(coverage)
            target_matches = (
                matched_skills if requirement.importance == "required" else bonus_skills
            )
            target_matches.extend(
                option.option
                for option in option_matches
                if option.matched_resume_skill is not None
            )
            if requirement.importance == "required" and (
                requirement.match_mode == "all" or status == "missing"
            ):
                missing_skills.extend(
                    SkillGap(skill=option.option, evidence=requirement.evidence)
                    for option in option_matches
                    if option.matched_resume_skill is None
                )

            matches.append(
                RequirementMatch(
                    label=requirement.label,
                    importance=requirement.importance,
                    match_mode=requirement.match_mode,
                    status=status,
                    options=option_matches,
                    job_evidence=requirement.evidence,
                )
            )

        score, required_score, preferred_score = self._group_scores(
            required_coverages,
            preferred_coverages,
        )
        return MatchReport(
            skill_coverage_score=score,
            required_score=required_score,
            preferred_score=preferred_score,
            matched_skills=list(dict.fromkeys(matched_skills)),
            bonus_skills=list(dict.fromkeys(bonus_skills)),
            missing_skills=missing_skills,
            priority_skills=missing_skills[:PRIORITY_LIMIT],
            requirement_matches=matches,
        )

    def _match_option(
        self,
        option: str,
        resume_index: dict[str, str],
        resume_text: str,
    ) -> SkillOptionMatch:
        canonical = self.normalizer.canonical_name(option)
        matched_skill = resume_index.get(canonical)
        evidence = self._resume_evidence(resume_text, matched_skill or option)
        if matched_skill is not None:
            return SkillOptionMatch(
                option=option,
                matched_resume_skill=matched_skill,
                resume_evidence=evidence,
            )
        if evidence is not None:
            surface = self.normalizer.find_evidence_surface(evidence, option) or option
            return SkillOptionMatch(
                option=option,
                matched_resume_skill=surface,
                resume_evidence=evidence,
            )
        return SkillOptionMatch(option=option)

    def _resume_evidence(self, resume_text: str, skill: str) -> str | None:
        for line in resume_text.splitlines():
            excerpt = line.strip()
            if excerpt and self.normalizer.contains_evidence(excerpt, skill):
                return excerpt
        return None

    def _match_v1(self, requirement, resume_skills: list[str]) -> MatchReport:
        """保留只读/预览兼容；V1 的持久化报告创建由服务层拒绝。"""
        resume_normalized = {self.normalizer.canonical_name(skill) for skill in resume_skills}
        evidence_by_skill = self._evidence_lookup(requirement.evidence)

        matched_skills = [
            skill
            for skill in requirement.required_skills
            if self.normalizer.canonical_name(skill) in resume_normalized
        ]
        bonus_skills = [
            skill
            for skill in requirement.preferred_skills
            if self.normalizer.canonical_name(skill) in resume_normalized
        ]
        missing_skills = [
            SkillGap(skill=skill, evidence=evidence_by_skill(skill))
            for skill in requirement.required_skills
            if self.normalizer.canonical_name(skill) not in resume_normalized
        ]

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

    @staticmethod
    def _group_scores(
        required_coverages: list[float],
        preferred_coverages: list[float],
    ) -> tuple[float | None, float | None, float | None]:
        if not required_coverages:
            return None, None, None
        required_coverage = sum(required_coverages) / len(required_coverages)
        if not preferred_coverages:
            score = round(required_coverage * 100, 1)
            return score, score, None
        required_score = round(required_coverage * REQUIRED_WEIGHT, 1)
        preferred_score = round(
            sum(preferred_coverages) / len(preferred_coverages) * PREFERRED_WEIGHT,
            1,
        )
        return round(required_score + preferred_score, 1), required_score, preferred_score

    def _evidence_lookup(self, evidence: list[str]) -> Callable[[str], str | None]:
        """返回用于查找技能支撑原文的函数。"""

        def find(skill: str) -> str | None:
            for excerpt in evidence:
                if self.normalizer.contains_evidence(excerpt, skill):
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
        """返回确定性的加权技能覆盖分数。"""
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
