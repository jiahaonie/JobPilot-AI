"""重排序端口。"""

from typing import Protocol

from app.rag.retrieval import RetrievedChunk


class Reranker(Protocol):
    """交叉编码器或模型重排序器的端口。"""

    def rerank(
        self,
        candidates: list[RetrievedChunk],
        query: str,
        *,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        """返回重排序后的候选项。"""


class IdentityReranker:
    """在加入经过评测的重排序器前使用的直通实现。"""

    def rerank(
        self,
        candidates: list[RetrievedChunk],
        query: str,
        *,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        del query
        return candidates[: max(top_k, 0)]
