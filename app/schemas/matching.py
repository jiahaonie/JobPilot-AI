"""Resume-to-job matching contracts."""

from pydantic import BaseModel, Field

SKILL_COVERAGE_DISCLAIMER = (
    "该分数仅表示简历对岗位技能要求的覆盖程度，"
    "不能直接解释为值得投递或录用概率。"
)


class SkillGap(BaseModel):
    """One required skill and the job text that supports it."""

    skill: str
    evidence: str | None = None


class MatchReport(BaseModel):
    """Explained skill comparison between a resume and one job."""

    skill_coverage_score: float | None
    required_score: float | None
    preferred_score: float | None
    score_disclaimer: str = SKILL_COVERAGE_DISCLAIMER
    matched_skills: list[str] = Field(default_factory=list)
    bonus_skills: list[str] = Field(default_factory=list)
    missing_skills: list[SkillGap] = Field(default_factory=list)
    priority_skills: list[SkillGap] = Field(default_factory=list)
