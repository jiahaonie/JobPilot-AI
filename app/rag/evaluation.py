"""离线评估套件使用的检索指标。"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalEvaluationCase:
    """单次查询的预期相关分块编号与返回排序。"""

    query: str
    relevant_chunk_ids: frozenset[str]
    retrieved_chunk_ids: tuple[str, ...]


@dataclass(frozen=True)
class RetrievalEvaluationSummary:
    """固定评估集上的平均 Recall@K 与 MRR。"""

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
    """返回前 K 个结果中找到的相关分块比例。"""
    _validate_metric_inputs(relevant_chunk_ids, k)
    hits = relevant_chunk_ids.intersection(retrieved_chunk_ids[:k])
    return len(hits) / len(relevant_chunk_ids)


def reciprocal_rank(
    retrieved_chunk_ids: Sequence[str],
    relevant_chunk_ids: set[str] | frozenset[str],
) -> float:
    """返回首个相关结果排名的倒数；未找到时返回零。"""
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
    """汇总可复现检索用例的 Recall@K 与 MRR。"""
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
