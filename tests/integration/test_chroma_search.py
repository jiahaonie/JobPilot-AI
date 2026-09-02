"""无需下载嵌入模型的本地 Chroma 真实往返测试。"""

import pytest

from app.rag.models import DocumentChunk
from app.rag.vector_store import ChromaVectorIndex
from app.services.search import KnowledgeSearchService


class DeterministicEmbedder:
    """在本地集成测试中运行真实 Chroma 适配器。"""

    def embed_query(self, query: str) -> list[float]:
        assert query == "FastAPI dependency injection"
        return [1.0, 0.0]


def test_real_chroma_upsert_query_filter_and_delete(tmp_path) -> None:
    index = ChromaVectorIndex(
        path=str(tmp_path / "chroma"),
        collection_name="real_round_trip",
    )
    chunks = [
        DocumentChunk(
            document_id="1",
            source_name="fastapi.md",
            chunk_index=0,
            text="FastAPI Depends dependency injection",
        ),
        DocumentChunk(
            document_id="2",
            source_name="docker.md",
            chunk_index=0,
            text="Docker image and container",
        ),
    ]
    index.upsert(chunks, [[1.0, 0.0], [0.0, 1.0]])

    service = KnowledgeSearchService(
        embedder=DeterministicEmbedder(),
        vector_index=index,
        default_max_distance=0.5,
    )
    response = service.search(query="FastAPI dependency injection", top_k=2)
    results = index.query([1.0, 0.0], top_k=2)

    assert [result.chunk.document_id for result in results] == ["1", "2"]
    assert results[0].distance == pytest.approx(0.0)
    assert results[1].distance == pytest.approx(1.0)
    assert [result.document_id for result in response.results] == [1]

    index.delete_document("1")
    remaining = index.query([1.0, 0.0], top_k=2)
    assert [result.chunk.document_id for result in remaining] == ["2"]
