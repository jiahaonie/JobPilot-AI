"""Semantic knowledge retrieval use case."""

from app.rag.embedding import Embedder
from app.rag.vector_store import VectorIndex
from app.schemas.knowledge import (
    KnowledgeSearchResponse,
    KnowledgeSearchResult,
)


class KnowledgeSearchService:
    """Embed one query, retrieve Top-K chunks, then reject distant matches."""

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
    ) -> KnowledgeSearchResponse:
        """Return only Chroma matches inside the configured cosine distance."""

        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("query cannot be empty")
        if top_k <= 0:
            raise ValueError("top_k must be positive")

        threshold = self.default_max_distance if max_distance is None else max_distance
        if not 0.0 <= threshold <= 2.0:
            raise ValueError("max_distance must be between 0 and 2")

        query_embedding = self.embedder.embed_query(normalized_query)
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
