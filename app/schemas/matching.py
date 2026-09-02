"""简历岗位匹配契约。"""

from pydantic import BaseModel, Field

SKILL_COVERAGE_DISCLAIMER = (
    "该分数仅表示简历对岗位技能要求的覆盖程度，不能直接解释为值得投递或录用概率。"
)


class SkillGap(BaseModel):
    """一项必需技能及其岗位原文依据。"""

    skill: str
    evidence: str | None = None


class MatchReport(BaseModel):
    """一份简历与一个岗位之间的可解释技能比较。"""

    skill_coverage_score: float | None
    required_score: float | None
    preferred_score: float | None
    score_disclaimer: str = SKILL_COVERAGE_DISCLAIMER
    matched_skills: list[str] = Field(default_factory=list)
    bonus_skills: list[str] = Field(default_factory=list)
    missing_skills: list[SkillGap] = Field(default_factory=list)
    priority_skills: list[SkillGap] = Field(default_factory=list)
