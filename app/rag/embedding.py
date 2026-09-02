"""嵌入端口与 FastEmbed 适配器。"""

from collections.abc import Iterable
from typing import Protocol

from fastembed import TextEmbedding


class Vector(Protocol):
    """描述 FastEmbed 返回向量的最小行为。"""

    def tolist(self) -> list[float]:
        """将模型专用向量转换为普通 Python 值。"""


class TextEmbeddingModel(Protocol):
    """应用使用的 FastEmbed 接口子集。"""

    def passage_embed(self, documents: list[str]) -> Iterable[Vector]:
        """为待存储文档段落生成嵌入。"""

    def query_embed(self, query: str) -> Iterable[Vector]:
        """为一条检索查询生成嵌入。"""


class Embedder(Protocol):
    """面向应用层的文本嵌入边界。"""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """为每段文档文本返回一个向量。"""

    def embed_query(self, query: str) -> list[float]:
        """为搜索查询返回一个向量。"""


class FastEmbedder:
    """使用可复用 FastEmbed 模型生成检索向量。"""

    def __init__(
        self,
        *,
        model_name: str,
        model: TextEmbeddingModel | None = None,
    ) -> None:
        self.model_name = model_name
        self.model = model or TextEmbedding(model_name=model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """为待存储分块使用段落嵌入。"""
        if not texts:
            return []

        if any(not text.strip() for text in texts):
            raise ValueError("document text cannot be empty")

        embeddings = [vector.tolist() for vector in self.model.passage_embed(texts)]
        if len(embeddings) != len(texts):
            raise ValueError("embedding count must match document count")
        return embeddings

    def embed_query(self, query: str) -> list[float]:
        """为检索输入使用查询专用嵌入路径。"""
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("query cannot be empty")

        embeddings = [vector.tolist() for vector in self.model.query_embed(normalized_query)]
        if len(embeddings) != 1:
            raise ValueError("query embedding must contain exactly one vector")
        return embeddings[0]
