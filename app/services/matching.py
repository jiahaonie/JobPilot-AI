"""Resume-to-job matching: pure logic, no LLM involved."""

from sqlalchemy.orm import Session

from app.core.exceptions import JobRequirementNotFoundError, ResourceNotFoundError
from app.repositories.job_requirement import JobRequirementRepository
from app.repositories.resume import ResumeRepository
from app.schemas.matching import MatchReport, SkillGap

PRIORITY_LIMIT = 3


def _normalize(skill: str) -> str:
    """Lowercase and strip internal whitespace for forgiving comparison."""

    return "".join(skill.lower().split())


class MatchService:
    """Compare a resume's skills against one job's structured requirements."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.job_requirement_repository = JobRequirementRepository(session)
        self.resume_repository = ResumeRepository(session)

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

        resume_normalized = {_normalize(skill) for skill in resume.skills}
        evidence_by_skill = self._evidence_lookup(requirement.evidence)

        matched_skills: list[str] = []
        for skill in requirement.required_skills:
            if _normalize(skill) in resume_normalized:
                matched_skills.append(skill)

        bonus_skills: list[str] = []
        for skill in requirement.preferred_skills:
            if _normalize(skill) in resume_normalized:
                bonus_skills.append(skill)

        missing_skills: list[SkillGap] = []
        for skill in requirement.required_skills:
            if _normalize(skill) not in resume_normalized:
                missing_skills.append(
                    SkillGap(skill=skill, evidence=evidence_by_skill(skill))
                )

        priority_skills = missing_skills[:PRIORITY_LIMIT]
        return MatchReport(
            matched_skills=matched_skills,
            bonus_skills=bonus_skills,
            missing_skills=missing_skills,
            priority_skills=priority_skills,
        )

    def _evidence_lookup(self, evidence: list[str]):
        """Return a function mapping a skill to its supporting job text."""

        def find(skill: str) -> str:
            for excerpt in evidence:
                if _normalize(skill) in _normalize(excerpt):
                    return excerpt
            return evidence[0] if evidence else ""

        return find
