"""纯逻辑简历岗位匹配器的单元测试。"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.exceptions import JobRequirementNotFoundError, ResourceNotFoundError
from app.models.base import Base
from app.models.job_requirement import JobRequirementRow
from app.models.resume import Resume
from app.services.matching import MatchService
from app.services.skill_normalization import SkillNormalizer


@pytest.fixture
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    yield session_factory()
    engine.dispose()


def make_requirement(session, job_id=1, required=None, preferred=None, evidence=None):
    row = JobRequirementRow(
        job_id=job_id,
        job_title="RAG Intern",
        required_skills=(["Python", "FastAPI", "Vector DB"] if required is None else required),
        preferred_skills=["NLP"] if preferred is None else preferred,
        evidence=(
            [
                "Proficient in Python.",
                "Experience with FastAPI.",
                "Knowledge of Vector DB.",
            ]
            if evidence is None
            else evidence
        ),
    )
    session.add(row)
    session.commit()
    return row


def make_resume(session, skills, resume_id=1):
    resume = Resume(
        id=resume_id,
        title="Resume",
        raw_text="x",
        skills=skills,
    )
    session.add(resume)
    session.commit()
    return resume


def make_v2_requirement(session, skill_requirements, job_id=1):
    row = JobRequirementRow(
        job_id=job_id,
        job_title="Agent Engineer",
        extraction_version="job-requirements-v2",
        skill_requirements=skill_requirements,
        unscored_requirements=[],
        required_skills=[
            option
            for requirement in skill_requirements
            if requirement["importance"] == "required"
            for option in requirement["options"]
        ],
        preferred_skills=[],
        evidence=[requirement["evidence"] for requirement in skill_requirements],
    )
    session.add(row)
    session.commit()
    return row


def test_unlisted_multiword_skill_keeps_original_surface_for_evidence() -> None:
    normalizer = SkillNormalizer()

    assert normalizer.contains_evidence(
        "熟悉Prompt Engineering技巧",
        "Prompt Engineering",
    )
    assert normalizer.find_evidence_surface(
        "熟悉Prompt Engineering技巧",
        "Prompt Engineering",
    ) == "Prompt Engineering"


def test_evidence_ignores_spacing_between_chinese_and_latin_text() -> None:
    normalizer = SkillNormalizer()

    assert normalizer.contains_evidence("具备多 Agent 协作经验", "多Agent协作")
    assert not normalizer.contains_evidence("使用 Django 开发服务", "Go")


def test_any_group_is_covered_when_one_option_matches(session) -> None:
    make_v2_requirement(
        session,
        [
            {
                "label": "主流编程语言",
                "importance": "required",
                "match_mode": "any",
                "options": ["Python", "TypeScript", "Go"],
                "evidence": "掌握 Python、TypeScript 或 Go。",
            },
            {
                "label": "提示词工程",
                "importance": "required",
                "match_mode": "all",
                "options": ["Prompt Engineering"],
                "evidence": "需要 Prompt Engineering。",
            },
        ],
    )
    make_resume(session, ["Python", "TypeScript", "Prompt Engineering"])

    report = MatchService(session).match(job_id=1, resume_id=1)

    assert report.skill_coverage_score == 100.0
    assert report.matched_skills == ["Python", "TypeScript", "Prompt Engineering"]
    assert report.missing_skills == []
    assert report.requirement_matches is not None
    assert report.requirement_matches[0].status == "covered"
    assert report.requirement_matches[1].status == "covered"


def test_all_group_reports_partial_coverage_and_missing_options(session) -> None:
    make_v2_requirement(
        session,
        [
            {
                "label": "Agent 核心机制",
                "importance": "required",
                "match_mode": "all",
                "options": ["Planning", "Memory", "Tool Use", "Reflection"],
                "evidence": "需要 Planning、Memory、Tool Use 和 Reflection。",
            }
        ],
    )
    resume = make_resume(session, ["Tool Calling"])
    resume.raw_text = "技能：Tool Calling"
    session.commit()

    report = MatchService(session).match(job_id=1, resume_id=1)

    assert report.skill_coverage_score == 25.0
    assert report.matched_skills == ["Tool Use"]
    assert [gap.skill for gap in report.missing_skills] == [
        "Planning",
        "Memory",
        "Reflection",
    ]
    assert report.requirement_matches is not None
    match = report.requirement_matches[0]
    assert match.status == "partial"
    assert match.options[2].matched_resume_skill == "Tool Calling"
    assert match.options[2].resume_evidence == "技能：Tool Calling"


def test_exact_resume_text_surface_can_recover_omitted_extracted_skill(session) -> None:
    make_v2_requirement(
        session,
        [
            {
                "label": "工作流",
                "importance": "required",
                "match_mode": "all",
                "options": ["Temporal"],
                "evidence": "熟悉 Temporal。",
            }
        ],
    )
    resume = make_resume(session, [])
    resume.raw_text = "项目技术栈：Temporal\n其他经历"
    session.commit()

    report = MatchService(session).match(job_id=1, resume_id=1)

    assert report.matched_skills == ["Temporal"]
    assert report.requirement_matches is not None
    assert report.requirement_matches[0].options[0].resume_evidence == "项目技术栈：Temporal"


def test_short_option_does_not_match_inside_resume_word(session) -> None:
    make_v2_requirement(
        session,
        [
            {
                "label": "Go",
                "importance": "required",
                "match_mode": "all",
                "options": ["Go"],
                "evidence": "需要 Go。",
            }
        ],
    )
    resume = make_resume(session, [])
    resume.raw_text = "使用 Django 开发服务"
    session.commit()

    report = MatchService(session).match(job_id=1, resume_id=1)

    assert report.matched_skills == []
    assert [gap.skill for gap in report.missing_skills] == ["Go"]


def test_matched_and_missing_skills(session) -> None:
    make_requirement(session)
    make_resume(session, ["Python"])

    report = MatchService(session).match(job_id=1, resume_id=1)

    assert report.matched_skills == ["Python"]
    assert [gap.skill for gap in report.missing_skills] == ["FastAPI", "Vector DB"]
    assert [gap.skill for gap in report.priority_skills] == ["FastAPI", "Vector DB"]


def test_matching_is_case_and_space_insensitive(session) -> None:
    make_requirement(session)
    make_resume(session, ["fast-api"])

    report = MatchService(session).match(job_id=1, resume_id=1)

    assert report.matched_skills == ["FastAPI"]


def test_chinese_skill_matches_approved_english_alias(session) -> None:
    make_requirement(
        session,
        required=["向量数据库"],
        preferred=[],
        evidence=["熟悉 Vector DB 和相关工具。"],
    )
    make_resume(session, ["Vector Database"])

    report = MatchService(session).match(job_id=1, resume_id=1)

    assert report.matched_skills == ["向量数据库"]
    assert report.missing_skills == []


def test_approved_alias_finds_job_evidence(session) -> None:
    make_requirement(
        session,
        required=["向量数据库"],
        preferred=[],
        evidence=["熟悉 Vector Database 和相关工具。"],
    )
    make_resume(session, [])

    report = MatchService(session).match(job_id=1, resume_id=1)

    assert report.missing_skills[0].evidence == "熟悉 Vector Database 和相关工具。"


@pytest.mark.parametrize(
    ("required_skill", "resume_skill"),
    [
        ("PostgreSQL", "MySQL"),
        ("向量数据库", "Chroma"),
    ],
)
def test_related_but_non_synonymous_skills_do_not_match(
    session,
    required_skill,
    resume_skill,
) -> None:
    make_requirement(
        session,
        required=[required_skill],
        preferred=[],
        evidence=[f"熟悉 {resume_skill}。"],
    )
    make_resume(session, [resume_skill])

    report = MatchService(session).match(job_id=1, resume_id=1)

    assert report.matched_skills == []
    assert [gap.skill for gap in report.missing_skills] == [required_skill]
    assert report.missing_skills[0].evidence is None


def test_missing_skill_returns_none_when_no_reliable_evidence(session) -> None:
    make_requirement(
        session,
        required=["PostgreSQL"],
        preferred=[],
        evidence=["熟悉 Python Web 开发。"],
    )
    make_resume(session, [])

    report = MatchService(session).match(job_id=1, resume_id=1)

    assert report.missing_skills[0].evidence is None


def test_short_skill_does_not_match_inside_another_word(session) -> None:
    make_requirement(
        session,
        required=["Go"],
        preferred=[],
        evidence=["使用 Django 开发 Web 服务。"],
    )
    make_resume(session, [])

    report = MatchService(session).match(job_id=1, resume_id=1)

    assert report.missing_skills[0].evidence is None


def test_bonus_skills_reports_preferred_satisfied(session) -> None:
    make_requirement(session)
    make_resume(session, ["NLP", "Vector DB"])

    report = MatchService(session).match(job_id=1, resume_id=1)

    assert report.bonus_skills == ["NLP"]
    assert report.matched_skills == ["Vector DB"]


def test_all_satisfied_gives_empty_missing(session) -> None:
    make_requirement(session)
    make_resume(session, ["Python", "FastAPI", "Vector DB"])

    report = MatchService(session).match(job_id=1, resume_id=1)

    assert report.missing_skills == []
    assert report.matched_skills == ["Python", "FastAPI", "Vector DB"]


def test_weighted_skill_coverage_score_uses_required_and_preferred(session) -> None:
    make_requirement(
        session,
        required=["Python", "FastAPI", "Docker"],
        preferred=["RAG", "LangChain"],
    )
    make_resume(session, ["Python", "Fast API", "RAG"])

    report = MatchService(session).match(job_id=1, resume_id=1)

    assert report.required_score == 53.3
    assert report.preferred_score == 10.0
    assert report.skill_coverage_score == 63.3
    assert "不能直接解释为值得投递或录用概率" in report.score_disclaimer


def test_required_coverage_becomes_final_score_without_preferred_skills(
    session,
) -> None:
    make_requirement(
        session,
        required=["Python", "FastAPI", "Docker"],
        preferred=[],
    )
    make_resume(session, ["Python", "Fast API"])

    report = MatchService(session).match(job_id=1, resume_id=1)

    assert report.required_score == 66.7
    assert report.preferred_score is None
    assert report.skill_coverage_score == 66.7


def test_score_is_unavailable_without_required_skills(session) -> None:
    make_requirement(session, required=[], preferred=["RAG"])
    make_resume(session, ["RAG"])

    report = MatchService(session).match(job_id=1, resume_id=1)

    assert report.required_score is None
    assert report.preferred_score is None
    assert report.skill_coverage_score is None


def test_priority_skills_limited_to_three(session) -> None:
    make_requirement(session, required=[f"Skill {i}" for i in range(5)])
    make_resume(session, [])

    report = MatchService(session).match(job_id=1, resume_id=1)

    assert [gap.skill for gap in report.priority_skills] == [
        "Skill 0",
        "Skill 1",
        "Skill 2",
    ]


def test_missing_job_requirement_raises(session) -> None:
    make_resume(session, ["Python"])

    with pytest.raises(JobRequirementNotFoundError):
        MatchService(session).match(job_id=1, resume_id=1)


def test_missing_resume_raises(session) -> None:
    make_requirement(session)

    with pytest.raises(ResourceNotFoundError):
        MatchService(session).match(job_id=1, resume_id=999)
