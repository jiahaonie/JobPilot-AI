"""Retrieval metrics used by the offline evaluation suite."""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalEvaluationCase:
    """Expected relevant chunk IDs and the ranking returned for one query."""

    query: str
    relevant_chunk_ids: frozenset[str]
    retrieved_chunk_ids: tuple[str, ...]


@dataclass(frozen=True)
class RetrievalEvaluationSummary:
    """Mean Recall@K and MRR over a fixed evaluation set."""

    case_count: int
    k: int
    recall_at_k: float
    mrr: float


def recall_at_k(
    retrieved_chunk_ids: Sequence[str],
    relevant_chunk_ids: set[str] | frozenset[str],
    *,
    k: int,
) -> float:
    """Return the fraction of relevant chunks found in the first K results."""

    _validate_metric_inputs(relevant_chunk_ids, k)
    hits = relevant_chunk_ids.intersection(retrieved_chunk_ids[:k])
    return len(hits) / len(relevant_chunk_ids)


def reciprocal_rank(
    retrieved_chunk_ids: Sequence[str],
    relevant_chunk_ids: set[str] | frozenset[str],
) -> float:
    """Return 1/rank for the first relevant result, or zero when none is found."""

    if not relevant_chunk_ids:
        raise ValueError("relevant_chunk_ids cannot be empty")
    for rank, chunk_id in enumerate(retrieved_chunk_ids, start=1):
        if chunk_id in relevant_chunk_ids:
            return 1.0 / rank
    return 0.0


def evaluate_retrieval(
    cases: Iterable[RetrievalEvaluationCase],
    *,
    k: int,
) -> RetrievalEvaluationSummary:
    """Aggregate Recall@K and MRR across reproducible retrieval cases."""

    materialized_cases = list(cases)
    if not materialized_cases:
        raise ValueError("at least one evaluation case is required")
    recalls = [
        recall_at_k(
            case.retrieved_chunk_ids,
            case.relevant_chunk_ids,
            k=k,
        )
        for case in materialized_cases
    ]
    reciprocal_ranks = [
        reciprocal_rank(case.retrieved_chunk_ids, case.relevant_chunk_ids)
        for case in materialized_cases
    ]
    return RetrievalEvaluationSummary(
        case_count=len(materialized_cases),
        k=k,
        recall_at_k=sum(recalls) / len(recalls),
        mrr=sum(reciprocal_ranks) / len(reciprocal_ranks),
    )


def _validate_metric_inputs(
    relevant_chunk_ids: set[str] | frozenset[str],
    k: int,
) -> None:
    if k <= 0:
        raise ValueError("k must be positive")
    if not relevant_chunk_ids:
        raise ValueError("relevant_chunk_ids cannot be empty")
