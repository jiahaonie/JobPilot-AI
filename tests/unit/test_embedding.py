"""Unit tests for the FastEmbed adapter without downloading a real model."""

from array import array
from collections.abc import Iterable

import pytest

from app.rag.embedding import FastEmbedder, Vector


class FakeTextEmbeddingModel:
    """Record which FastEmbed path the adapter selects."""

    def __init__(self) -> None:
        self.passage_inputs: list[str] = []
        self.query_inputs: list[str] = []

    def passage_embed(self, documents: list[str]) -> Iterable[Vector]:
        self.passage_inputs = documents
        return (array("f", [float(len(text)), 1.0]) for text in documents)

    def query_embed(self, query: str) -> Iterable[Vector]:
        self.query_inputs.append(query)
        return iter([array("f", [float(len(query)), 2.0])])


def test_embed_documents_uses_passage_embeddings() -> None:
    model = FakeTextEmbeddingModel()
    embedder = FastEmbedder(model_name="fake-model", model=model)

    embeddings = embedder.embed_documents(["FastAPI", "依赖注入"])

    assert model.passage_inputs == ["FastAPI", "依赖注入"]
    assert embeddings == [[7.0, 1.0], [4.0, 1.0]]


def test_embed_query_uses_query_embedding() -> None:
    model = FakeTextEmbeddingModel()
    embedder = FastEmbedder(model_name="fake-model", model=model)

    embedding = embedder.embed_query("  如何使用 Depends？  ")

    assert model.query_inputs == ["如何使用 Depends？"]
    assert embedding == [13.0, 2.0]


def test_embed_query_rejects_blank_text() -> None:
    embedder = FastEmbedder(
        model_name="fake-model",
        model=FakeTextEmbeddingModel(),
    )

    with pytest.raises(ValueError, match="query cannot be empty"):
        embedder.embed_query("   ")


def test_embed_documents_rejects_blank_text()-> None:
    model = FakeTextEmbeddingModel()
    embedder = FastEmbedder(model_name="fake-model", model=model)

    with pytest.raises(ValueError, match="document text cannot be empty"):
        embedder.embed_documents(["FastAPI", "   "])

    assert model.passage_inputs == []
