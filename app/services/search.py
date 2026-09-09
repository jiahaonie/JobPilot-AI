"""知识库语义检索用例。"""

from app.rag.embedding import Embedder
from app.rag.vector_store import VectorIndex
from app.schemas.knowledge import (
    KnowledgeSearchResponse,
    KnowledgeSearchResult,
)


class KnowledgeSearchService:
    """嵌入查询、检索 Top-K 片段，并过滤距离过大的结果。"""

    def __init__(
        self,
        *,
        embedder: Embedder,
        vector_index: VectorIndex,
        default_max_distance: float,
    ) -> None:
        self.embedder = embedder
        self.vector_index = vector_index
        self.default_max_distance = default_max_distance

    def search(
        self,
        *,
        query: str,
        top_k: int = 5,
        max_distance: float | None = None,
        document_ids: list[int] | None = None,
    ) -> KnowledgeSearchResponse:
        """仅返回余弦距离在配置阈值内的 Chroma 匹配。"""
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("query cannot be empty")
        if top_k <= 0:
            raise ValueError("top_k must be positive")

        threshold = self.default_max_distance if max_distance is None else max_distance
        if not 0.0 <= threshold <= 2.0:
            raise ValueError("max_distance must be between 0 and 2")

        query_embedding = self.embedder.embed_query(normalized_query)
        if document_ids:
            matches = self.vector_index.query(
                query_embedding,
                top_k=top_k,
                document_ids=[str(document_id) for document_id in document_ids],
            )
        else:
            matches = self.vector_index.query(query_embedding, top_k=top_k)
        results = [
            KnowledgeSearchResult(
                chunk_id=match.chunk_id,
                document_id=int(match.chunk.document_id),
                source_name=match.chunk.source_name,
                chunk_index=match.chunk.chunk_index,
                text=match.chunk.text,
                distance=match.distance,
            )
            for match in matches
            if match.distance <= threshold
        ]
        return KnowledgeSearchResponse(
            query=normalized_query,
            max_distance=threshold,
            results=results,
        )
