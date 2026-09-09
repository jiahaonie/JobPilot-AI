"""无需创建真实数据库的 Chroma 适配器单元测试。"""

from typing import Any

from app.rag.models import DocumentChunk
from app.rag.vector_store import ChromaVectorIndex


class FakeChromaCollection:
    """记录 Chroma 调用并返回可配置查询载荷。"""

    def __init__(self) -> None:
        self.upsert_call: dict[str, Any] | None = None
        self.query_call: dict[str, Any] | None = None
        self.delete_call: dict[str, Any] | None = None
        self.query_payload: dict[str, Any] = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

    def upsert(self, **kwargs: Any) -> None:
        self.upsert_call = kwargs

    def query(self, **kwargs: Any) -> dict[str, Any]:
        self.query_call = kwargs
        return self.query_payload

    def delete(self, **kwargs: Any) -> None:
        self.delete_call = kwargs


def test_upsert_writes_parallel_chunk_fields() -> None:
    collection = FakeChromaCollection()
    index = ChromaVectorIndex(
        path="unused",
        collection_name="test",
        collection=collection,
    )
    chunks = [
        DocumentChunk(
            document_id="7",
            source_name="notes.md",
            chunk_index=0,
            text="FastAPI 使用 Depends。",
            metadata={"section": "依赖注入"},
        ),
        DocumentChunk(
            document_id="7",
            source_name="notes.md",
            chunk_index=1,
            text="SQLAlchemy 管理数据库。",
        ),
    ]

    index.upsert(chunks, [[0.1, 0.2], [0.3, 0.4]])

    assert collection.upsert_call == {
        "ids": ["document:7:chunk:0", "document:7:chunk:1"],
        "embeddings": [[0.1, 0.2], [0.3, 0.4]],
        "documents": ["FastAPI 使用 Depends。", "SQLAlchemy 管理数据库。"],
        "metadatas": [
            {
                "section": "依赖注入",
                "document_id": "7",
                "source_name": "notes.md",
                "chunk_index": 0,
            },
            {
                "document_id": "7",
                "source_name": "notes.md",
                "chunk_index": 1,
            },
        ],
    }


def test_query_maps_first_chroma_batch_to_chunks() -> None:
    collection = FakeChromaCollection()
    collection.query_payload = {
        "ids": [["document:7:chunk:0"]],
        "documents": [["FastAPI 使用 Depends。"]],
        "metadatas": [
            [
                {
                    "document_id": "7",
                    "source_name": "notes.md",
                    "chunk_index": 0,
                    "section": "依赖注入",
                }
            ]
        ],
        "distances": [[0.15]],
    }
    index = ChromaVectorIndex(
        path="unused",
        collection_name="test",
        collection=collection,
    )

    results = index.query([0.1, 0.2], top_k=3)

    assert collection.query_call == {
        "query_embeddings": [[0.1, 0.2]],
        "n_results": 3,
        "include": ["documents", "metadatas", "distances"],
    }
    assert len(results) == 1
    assert results[0].chunk_id == "document:7:chunk:0"
    assert results[0].chunk.text == "FastAPI 使用 Depends。"
    assert results[0].chunk.metadata == {"section": "依赖注入"}
    assert results[0].distance == 0.15


def test_query_filters_allowed_documents_before_top_k() -> None:
    collection = FakeChromaCollection()
    index = ChromaVectorIndex(
        path="unused",
        collection_name="test",
        collection=collection,
    )

    index.query([0.1, 0.2], top_k=5, document_ids=["3", "7"])

    assert collection.query_call is not None
    assert collection.query_call["where"] == {"document_id": {"$in": ["3", "7"]}}


def test_delete_document_uses_metadata_filter() -> None:
    collection = FakeChromaCollection()
    index = ChromaVectorIndex(
        path="unused",
        collection_name="test",
        collection=collection,
    )

    index.delete_document("7")

    assert collection.delete_call == {"where": {"document_id": "7"}}
