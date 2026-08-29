"""Job analysis use case: raw JD to structured requirements via an LLM."""

import logging

from sqlalchemy.orm import Session

from app.core.exceptions import LLMAnalysisError
from app.llm.client import StructuredLLMClient
from app.llm.exceptions import LLMError
from app.llm.prompts import build_job_requirement_prompt
from app.models.job_requirement import JobRequirementRow
from app.repositories.job_requirement import JobRequirementRepository
from app.schemas.requirements import JobRequirement
from app.services.job import JobService

logger = logging.getLogger(__name__)


class JobAnalysisService:
    """Coordinate LLM analysis and keep provider concerns out of the routes."""

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
        """Extract structured requirements from a saved job description."""

        job = self.job_service.get(job_id)
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
            raise LLMAnalysisError(f"Job analysis failed: {exc}") from exc
        if not result.evidence:
            result.evidence = [job.raw_text]
        self._persist(job_id, result)
        return result

    def _persist(self, job_id: int, result: JobRequirement) -> None:
        """Save the latest analysis; never block a valid result on a write."""

        row = JobRequirementRow(
            job_id=job_id,
            job_title=result.job_title,
            required_skills=result.required_skills,
            preferred_skills=result.preferred_skills,
            education=result.education,
            internship_duration=result.internship_duration,
            responsibilities=result.responsibilities,
            evidence=result.evidence,
        )
        try:
            self.requirement_repository.upsert(row)
            self.session.commit()
        except Exception:
            self.session.rollback()
            logger.exception("Failed to persist job requirements for job %s", job_id)
