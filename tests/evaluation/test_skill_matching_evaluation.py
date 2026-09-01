"""Small human-reviewed evaluation set for deterministic skill aliases."""

from dataclasses import dataclass

from app.services.skill_normalization import SkillNormalizer


@dataclass(frozen=True, slots=True)
class SkillEquivalenceCase:
    left: str
    right: str
    expected_match: bool


EVALUATION_CASES = (
    SkillEquivalenceCase("FastAPI", "Fast API", True),
    SkillEquivalenceCase("FAST-API", "fastapi", True),
    SkillEquivalenceCase("向量数据库", "Vector DB", True),
    SkillEquivalenceCase("向量数据库", "Vector Database", True),
    SkillEquivalenceCase("LLM", "大语言模型", True),
    SkillEquivalenceCase("LLM", "Large Language Model", True),
    SkillEquivalenceCase("PostgreSQL", "MySQL", False),
    SkillEquivalenceCase("FastAPI", "Flask", False),
    SkillEquivalenceCase("向量数据库", "Chroma", False),
    SkillEquivalenceCase("RAG", "LangChain", False),
)


def test_curated_skill_alias_evaluation_has_no_false_or_missed_matches() -> None:
    normalizer = SkillNormalizer()

    predictions = [
        normalizer.equivalent(case.left, case.right) for case in EVALUATION_CASES
    ]
    expected = [case.expected_match for case in EVALUATION_CASES]

    true_positives = sum(
        predicted and label
        for predicted, label in zip(predictions, expected, strict=True)
    )
    predicted_positives = sum(predictions)
    actual_positives = sum(expected)
    precision = true_positives / predicted_positives
    recall = true_positives / actual_positives

    assert predictions == expected
    assert precision == 1.0
    assert recall == 1.0
