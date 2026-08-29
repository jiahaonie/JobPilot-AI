"""Embedding port and FastEmbed adapter."""

from collections.abc import Iterable
from typing import Protocol

from fastembed import TextEmbedding


class Vector(Protocol):
    """Minimal vector behavior returned by FastEmbed."""

    def tolist(self) -> list[float]:
        """Convert the model-specific vector into plain Python values."""


class TextEmbeddingModel(Protocol):
    """Subset of FastEmbed used by the application."""

    def passage_embed(self, documents: list[str]) -> Iterable[Vector]:
        """Embed stored document passages."""

    def query_embed(self, query: str) -> Iterable[Vector]:
        """Embed one retrieval query."""


class Embedder(Protocol):
    """Application-facing text embedding boundary."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one vector for every document text."""

    def embed_query(self, query: str) -> list[float]:
        """Return one vector for a search query."""


class FastEmbedder:
    """Generate retrieval vectors with a reusable FastEmbed model."""

    def __init__(
        self,
        *,
        model_name: str,
        model: TextEmbeddingModel | None = None,
    ) -> None:
        self.model_name = model_name
        self.model = model or TextEmbedding(model_name=model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Use passage embeddings for chunks that will be stored."""

        if not texts:
            return []

        if any(not text.strip() for text in texts):
            raise ValueError("document text cannot be empty")

        embeddings = [vector.tolist() for vector in self.model.passage_embed(texts)]
        if len(embeddings) != len(texts):
            raise ValueError("embedding count must match document count")
        return embeddings

    def embed_query(self, query: str) -> list[float]:
        """Use the query-specific embedding path for retrieval input."""

        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("query cannot be empty")

        embeddings = [vector.tolist() for vector in self.model.query_embed(normalized_query)]
        if len(embeddings) != 1:
            raise ValueError("query embedding must contain exactly one vector")
        return embeddings[0]
