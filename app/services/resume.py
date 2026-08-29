"""Resume use cases: save a resume and extract its skills via an LLM."""

from sqlalchemy.orm import Session

from app.core.exceptions import LLMAnalysisError, ResourceNotFoundError
from app.llm.client import StructuredLLMClient
from app.llm.exceptions import LLMError
from app.llm.prompts import build_resume_skill_prompt
from app.models.resume import Resume
from app.repositories.resume import ResumeRepository
from app.schemas.resume import ResumeCreate, ResumeSkill


class ResumeService:
    """Coordinate resume persistence and keep provider concerns out of routes."""

    def __init__(
        self,
        session: Session,
        client: StructuredLLMClient,
    ) -> None:
        self.session = session
        self.client = client
        self.repository = ResumeRepository(session)

    def create(self, payload: ResumeCreate) -> Resume:
        """Extract skills from the resume text, then persist the resume."""

        skills = self._extract_skills(payload.raw_text)
        resume = Resume(
            title=payload.title or _default_title(payload.raw_text),
            raw_text=payload.raw_text,
            skills=skills,
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

    def _extract_skills(self, raw_text: str) -> list[str]:
        """Ask the LLM to extract skills, failing the request on provider errors."""

        prompt = build_resume_skill_prompt(raw_text)
        try:
            result = self.client.complete_structured(
                prompt=prompt,
                response_model=ResumeSkill,
            )
        except LLMError as exc:
            raise LLMAnalysisError(
                f"Skill extraction failed: {exc}"
            ) from exc
        return result.skills


def _default_title(raw_text: str) -> str:
    """Derive a readable title from the start of the resume text."""

    compact = " ".join(raw_text.split())
    return compact[:20] or "未命名简历"
