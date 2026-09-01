"""Create and read immutable match-report snapshots."""

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundError
from app.models.match_report import MatchReportRow
from app.repositories.job_requirement import JobRequirementRepository
from app.repositories.match_report import MatchReportRepository
from app.repositories.resume import ResumeRepository
from app.services.matching import MatchService

SCORING_VERSION = "skill-coverage-v1"


class MatchReportService:
    """Persist matching results without coupling storage to MatchService."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.match_service = MatchService(session)
        self.requirement_repository = JobRequirementRepository(session)
        self.resume_repository = ResumeRepository(session)
        self.report_repository = MatchReportRepository(session)

    def create(self, *, job_id: int, resume_id: int) -> MatchReportRow:
        """Calculate a match and save all inputs needed to explain it later."""

        result = self.match_service.match(job_id=job_id, resume_id=resume_id)
        requirement = self.requirement_repository.get_by_job(job_id)
        resume = self.resume_repository.get(resume_id)
        if requirement is None or resume is None:
            raise RuntimeError("matching sources disappeared during report creation")

        report = MatchReportRow(
            job_id=job_id,
            resume_id=resume_id,
            skill_coverage_score=result.skill_coverage_score,
            required_score=result.required_score,
            preferred_score=result.preferred_score,
            score_disclaimer=result.score_disclaimer,
            matched_skills=list(result.matched_skills),
            bonus_skills=list(result.bonus_skills),
            missing_skills=[gap.model_dump(mode="json") for gap in result.missing_skills],
            priority_skills=[gap.model_dump(mode="json") for gap in result.priority_skills],
            required_skills_snapshot=list(requirement.required_skills),
            preferred_skills_snapshot=list(requirement.preferred_skills),
            resume_skills_snapshot=list(resume.skills),
            job_requirement_updated_at=requirement.updated_at,
            resume_analyzed_at=resume.analyzed_at,
            scoring_version=SCORING_VERSION,
        )
        self.report_repository.add(report)
        self.session.commit()
        self.session.refresh(report)
        return report

    def get(self, report_id: int) -> MatchReportRow:
        """Return one stored report or a domain-level not-found error."""

        report = self.report_repository.get(report_id)
        if report is None:
            raise ResourceNotFoundError(f"Match report {report_id} was not found")
        return report

    def list(
        self,
        *,
        job_id: int | None = None,
        resume_id: int | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[MatchReportRow]:
        """Return stored reports using bounded optional filters."""

        return self.report_repository.list(
            job_id=job_id,
            resume_id=resume_id,
            offset=offset,
            limit=limit,
        )
