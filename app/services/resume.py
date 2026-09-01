"""Resume persistence and independently triggered skill analysis."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import LLMAnalysisError, ResourceNotFoundError
from app.llm.client import StructuredLLMClient
from app.llm.exceptions import LLMError
from app.llm.prompts import build_resume_skill_prompt
from app.models.enums import ResumeAnalysisStatus
from app.models.resume import Resume
from app.models.resume_analysis import ResumeAnalysis
from app.repositories.resume import ResumeRepository
from app.schemas.resume import ResumeCreate, ResumeSkill


class ResumeService:
    """Persist and manage resumes without requiring an LLM provider."""

    def __init__(
        self,
        session: Session,
    ) -> None:
        self.session = session
        self.repository = ResumeRepository(session)

    def create(self, payload: ResumeCreate) -> Resume:
        """Persist source text first and leave skill analysis pending."""

        resume = Resume(
            title=payload.title or _default_title(payload.raw_text),
            raw_text=payload.raw_text,
            skills=[],
            analysis=ResumeAnalysis(status=ResumeAnalysisStatus.PENDING),
        )
        self.repository.add(resume)
        self.session.commit()
        self.session.refresh(resume)
        return resume

    def get(self, resume_id: int) -> Resume:
        """Return a resume or raise a domain-level not-found error."""

        resume = self.repository.get(resume_id)
        if resume is None:
            raise ResourceNotFoundError(f"Resume {resume_id} was not found")
        return resume

    def list_all(self) -> list[Resume]:
        """Return all saved resumes."""

        return self.repository.list()

    def delete(self, resume_id: int) -> None:
        """Delete a saved resume."""

        resume = self.get(resume_id)
        self.repository.delete(resume)
        self.session.commit()


class ResumeAnalysisService:
    """Run and persist retryable LLM analysis for an already saved resume."""

    def __init__(
        self,
        session: Session,
        client: StructuredLLMClient,
    ) -> None:
        self.session = session
        self.client = client
        self.resume_service = ResumeService(session)

    def analyze(self, resume_id: int) -> Resume:
        """Extract skills and record ready or failed lifecycle state."""

        resume = self.resume_service.get(resume_id)
        analysis = resume.analysis
        if analysis is None:
            analysis = ResumeAnalysis(resume_id=resume.id)
            resume.analysis = analysis

        analysis.status = ResumeAnalysisStatus.ANALYZING
        analysis.error_message = None
        self.session.commit()

        try:
            skills = self._extract_skills(resume.raw_text)
        except LLMError as exc:
            analysis.status = ResumeAnalysisStatus.FAILED
            analysis.error_message = str(exc)
            self.session.commit()
            raise LLMAnalysisError(f"Skill extraction failed: {exc}") from exc

        resume.skills = skills
        analysis.status = ResumeAnalysisStatus.READY
        analysis.error_message = None
        analysis.analyzed_at = datetime.now(UTC)
        self.session.commit()
        self.session.refresh(resume)
        return resume

    def _extract_skills(self, raw_text: str) -> list[str]:
        """Ask the LLM for a schema-validated skill list."""

        prompt = build_resume_skill_prompt(raw_text)
        result = self.client.complete_structured(
            prompt=prompt,
            response_model=ResumeSkill,
        )
        return result.skills


def _default_title(raw_text: str) -> str:
    """Derive a readable title from the start of the resume text."""

    compact = " ".join(raw_text.split())
    return compact[:20] or "未命名简历"
