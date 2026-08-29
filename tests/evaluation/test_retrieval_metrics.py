"""Deterministic offline checks for retrieval quality metrics."""

import pytest

from app.rag.evaluation import (
    RetrievalEvaluationCase,
    evaluate_retrieval,
    recall_at_k,
    reciprocal_rank,
)


def test_recall_at_k_counts_all_relevant_chunks_in_top_k() -> None:
    assert recall_at_k(
        ["chunk-a", "noise", "chunk-b"],
        {"chunk-a", "chunk-b"},
        k=2,
    ) == 0.5


def test_reciprocal_rank_uses_first_relevant_position() -> None:
    assert reciprocal_rank(
        ["noise-a", "chunk-b", "chunk-a"],
        {"chunk-a", "chunk-b"},
    ) == 0.5


def test_evaluate_retrieval_averages_recall_and_mrr() -> None:
    summary = evaluate_retrieval(
        [
            RetrievalEvaluationCase(
                query="FastAPI 依赖注入",
                relevant_chunk_ids=frozenset({"fastapi"}),
                retrieved_chunk_ids=("fastapi", "noise"),
            ),
            RetrievalEvaluationCase(
                query="SQLAlchemy 事务",
                relevant_chunk_ids=frozenset({"sqlalchemy"}),
                retrieved_chunk_ids=("noise", "sqlalchemy"),
            ),
        ],
        k=1,
    )

    assert summary.case_count == 2
    assert summary.recall_at_k == 0.5
    assert summary.mrr == 0.75


def test_metrics_reject_cases_without_relevance_judgments() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        recall_at_k(["noise"], set(), k=1)
