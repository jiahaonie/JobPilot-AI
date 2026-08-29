"""Reranking port."""

from typing import Protocol

from app.rag.retrieval import RetrievedChunk


class Reranker(Protocol):
    """Port for a cross-encoder or model-based reranker."""

    def rerank(
        self,
        candidates: list[RetrievedChunk],
        query: str,
        *,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        """Return reranked candidates."""


class IdentityReranker:
    """Pass-through implementation until a measured reranker is added."""

    def rerank(
        self,
        candidates: list[RetrievedChunk],
        query: str,
        *,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        del query
        return candidates[:max(top_k, 0)]
