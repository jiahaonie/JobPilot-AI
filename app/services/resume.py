"""简历持久化与独立触发的技能分析。"""

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
    """在不依赖 LLM 服务商的情况下保存和管理简历。"""

    def __init__(
        self,
        session: Session,
    ) -> None:
        self.session = session
        self.repository = ResumeRepository(session)

    def create(self, payload: ResumeCreate) -> Resume:
        """先保存原始文本，并将技能分析保持为待处理状态。"""
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
        """返回简历；不存在时抛出领域层未找到异常。"""
        resume = self.repository.get(resume_id)
        if resume is None:
            raise ResourceNotFoundError(f"Resume {resume_id} was not found")
        return resume

    def list_all(self, *, offset: int = 0, limit: int = 100) -> list[Resume]:
        """返回数量受限的已保存简历。"""
        return self.repository.list(offset=offset, limit=limit)

    def delete(self, resume_id: int) -> None:
        """删除一份已保存的简历。"""
        resume = self.get(resume_id)
        self.repository.delete(resume)
        self.session.commit()


class ResumeAnalysisService:
    """对已保存简历执行可重试的 LLM 分析并持久化结果。"""

    def __init__(
        self,
        session: Session,
        client: StructuredLLMClient,
    ) -> None:
        self.session = session
        self.client = client
        self.resume_service = ResumeService(session)

    def analyze(self, resume_id: int) -> Resume:
        """提取技能，并记录就绪或失败的生命周期状态。"""
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
        except Exception as exc:
            analysis.status = ResumeAnalysisStatus.FAILED
            analysis.error_message = "Unexpected analysis failure"
            self.session.commit()
            raise LLMAnalysisError("Skill extraction failed unexpectedly") from exc

        resume.skills = skills
        analysis.status = ResumeAnalysisStatus.READY
        analysis.error_message = None
        analysis.analyzed_at = datetime.now(UTC)
        self.session.commit()
        self.session.refresh(resume)
        return resume

    def _extract_skills(self, raw_text: str) -> list[str]:
        """请求 LLM 返回经过结构校验的技能列表。"""
        prompt = build_resume_skill_prompt(raw_text)
        result = self.client.complete_structured(
            prompt=prompt,
            response_model=ResumeSkill,
        )
        return result.skills


def _default_title(raw_text: str) -> str:
    """根据简历文本开头生成可读标题。"""
    compact = " ".join(raw_text.split())
    return compact[:20] or "未命名简历"
