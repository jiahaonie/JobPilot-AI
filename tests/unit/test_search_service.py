"""语义检索与无关结果过滤的单元测试。"""

from app.rag.models import DocumentChunk
from app.rag.vector_store import VectorSearchResult
from app.services.search import KnowledgeSearchService


class RecordingEmbedder:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def embed_query(self, query: str) -> list[float]:
        self.queries.append(query)
        return [1.0, 0.0]


class RecordingVectorIndex:
    def __init__(self, results: list[VectorSearchResult]) -> None:
        self.results = results
        self.query_calls: list[tuple[list[float], int]] = []

    def query(
        self,
        query_embedding: list[float],
        *,
        top_k: int = 5,
    ) -> list[VectorSearchResult]:
        self.query_calls.append((query_embedding, top_k))
        return self.results[:top_k]


def _result(chunk_id: str, distance: float) -> VectorSearchResult:
    return VectorSearchResult(
        chunk_id=chunk_id,
        chunk=DocumentChunk(
            document_id="7",
            source_name="notes.md",
            chunk_index=0,
            text=f"text for {chunk_id}",
        ),
        distance=distance,
    )


def test_search_uses_query_embedding_top_k_and_distance_threshold() -> None:
    embedder = RecordingEmbedder()
    index = RecordingVectorIndex([_result("relevant", 0.18), _result("irrelevant", 0.81)])
    service = KnowledgeSearchService(
        embedder=embedder,
        vector_index=index,
        default_max_distance=0.45,
    )

    response = service.search(query="  FastAPI Depends  ", top_k=2)

    assert embedder.queries == ["FastAPI Depends"]
    assert index.query_calls == [([1.0, 0.0], 2)]
    assert [result.chunk_id for result in response.results] == ["relevant"]
    assert response.max_distance == 0.45


def test_search_allows_request_specific_distance_threshold() -> None:
    index = RecordingVectorIndex([_result("borderline", 0.6)])
    service = KnowledgeSearchService(
        embedder=RecordingEmbedder(),
        vector_index=index,
        default_max_distance=0.45,
    )

    response = service.search(query="SQLAlchemy", top_k=1, max_distance=0.7)

    assert [result.chunk_id for result in response.results] == ["borderline"]
