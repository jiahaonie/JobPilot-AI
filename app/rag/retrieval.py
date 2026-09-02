"""检索端口与无依赖词法基线。"""

import re
from typing import Protocol

from pydantic import BaseModel

from app.rag.models import DocumentChunk


class RetrievedChunk(BaseModel):
    """带检索分数的分块。"""

    chunk: DocumentChunk
    score: float


class Retriever(Protocol):
    """向量、混合或词法检索实现的端口。"""

    def retrieve(
        self,
        chunks: list[DocumentChunk],
        query: str,
        *,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        """返回最相关的分块。"""


class LexicalRetriever:
    """选择嵌入存储前可用的小型本地基线。"""

    def retrieve(
        self,
        chunks: list[DocumentChunk],
        query: str,
        *,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        if top_k <= 0:
            return []
        terms = set(re.findall(r"\w+", query.lower()))
        if not terms:
            return []

        results: list[RetrievedChunk] = []
        for chunk in chunks:
            chunk_terms = set(re.findall(r"\w+", chunk.text.lower()))
            overlap = terms & chunk_terms
            if overlap:
                results.append(
                    RetrievedChunk(
                        chunk=chunk,
                        score=len(overlap) / len(terms),
                    )
                )
        return sorted(
            results,
            key=lambda item: (item.score, -item.chunk.chunk_index),
            reverse=True,
        )[:top_k]
