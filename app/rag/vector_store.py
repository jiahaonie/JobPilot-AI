"""向量索引端口与 Chroma 适配器。"""

from typing import Any, Protocol

import chromadb
from pydantic import BaseModel

from app.rag.models import DocumentChunk


class ChromaCollection(Protocol):
    """应用使用的 Chroma 集合接口子集。"""

    def upsert(
        self,
        *,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        """创建或替换分块记录。"""

    def query(
        self,
        *,
        query_embeddings: list[list[float]],
        n_results: int,
        include: list[str],
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """为一批查询向量返回最近记录。"""

    def delete(self, *, where: dict[str, Any]) -> None:
        """删除符合元数据条件的记录。"""


class VectorSearchResult(BaseModel):
    """一条带余弦距离的 Chroma 匹配。"""

    chunk_id: str
    chunk: DocumentChunk
    distance: float


class VectorIndex(Protocol):
    """面向应用层的向量持久化边界。"""

    def upsert(
        self,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
    ) -> None:
        """保存分块及其预计算嵌入。"""

    def query(
        self,
        query_embedding: list[float],
        *,
        top_k: int = 5,
        document_ids: list[str] | None = None,
    ) -> list[VectorSearchResult]:
        """返回最近的已存储分块。"""

    def delete_document(self, document_id: str) -> None:
        """删除属于一个源文档的全部分块。"""


class ChromaVectorIndex:
    """在 Chroma 集合中保存预计算向量与分块文本。"""

    def __init__(
        self,
        *,
        path: str,
        collection_name: str,
        collection: ChromaCollection | None = None,
    ) -> None:
        self.client: Any | None = None
        if collection is not None:
            self.collection = collection
            return

        self.client = chromadb.PersistentClient(path=path)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=None,
            configuration={"hnsw": {"space": "cosine"}},
        )

    def upsert(
        self,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
    ) -> None:
        """使用确定性编号写入对应的分块字段。"""
        if not chunks:
            return

        self.collection.upsert(
            ids=[self._chunk_id(chunk) for chunk in chunks],
            embeddings=embeddings,
            documents=[chunk.text for chunk in chunks],
            metadatas=[self._metadata(chunk) for chunk in chunks],
        )

    def query(
        self,
        query_embedding: list[float],
        *,
        top_k: int = 5,
        document_ids: list[str] | None = None,
    ) -> list[VectorSearchResult]:
        """将 Chroma 首批查询结果映射回领域对象。"""
        if not query_embedding or top_k <= 0:
            return []

        query_options: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"],
        }
        if document_ids:
            query_options["where"] = (
                {"document_id": document_ids[0]}
                if len(document_ids) == 1
                else {"document_id": {"$in": document_ids}}
            )
        payload = self.collection.query(
            **query_options,
        )
        return self._map_first_batch(payload)

    def delete_document(self, document_id: str) -> None:
        """删除与一个 SQLite 文档关联的全部向量。"""
        self.collection.delete(where={"document_id": document_id})

    @staticmethod
    def _chunk_id(chunk: DocumentChunk) -> str:
        return f"document:{chunk.document_id}:chunk:{chunk.chunk_index}"

    @staticmethod
    def _metadata(chunk: DocumentChunk) -> dict[str, Any]:
        return {
            **chunk.metadata,
            "document_id": chunk.document_id,
            "source_name": chunk.source_name,
            "chunk_index": chunk.chunk_index,
        }

    @staticmethod
    def _map_first_batch(payload: dict[str, Any]) -> list[VectorSearchResult]:
        ids = (payload.get("ids") or [[]])[0]
        documents = (payload.get("documents") or [[]])[0]
        metadatas = (payload.get("metadatas") or [[]])[0]
        distances = (payload.get("distances") or [[]])[0]

        if not (len(ids) == len(documents) == len(metadatas) == len(distances)):
            raise ValueError("Chroma query fields must have matching lengths")

        results: list[VectorSearchResult] = []
        core_keys = {"document_id", "source_name", "chunk_index"}
        for chunk_id, text, metadata, distance in zip(
            ids,
            documents,
            metadatas,
            distances,
            strict=True,
        ):
            if text is None or metadata is None or distance is None:
                raise ValueError("Chroma query returned an incomplete record")

            results.append(
                VectorSearchResult(
                    chunk_id=chunk_id,
                    chunk=DocumentChunk(
                        document_id=str(metadata["document_id"]),
                        source_name=str(metadata["source_name"]),
                        chunk_index=int(metadata["chunk_index"]),
                        text=text,
                        metadata={
                            str(key): str(value)
                            for key, value in metadata.items()
                            if key not in core_keys
                        },
                    ),
                    distance=float(distance),
                )
            )
        return results
