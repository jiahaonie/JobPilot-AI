"""Retrieval port and a dependency-free lexical baseline."""

import re
from typing import Protocol

from pydantic import BaseModel

from app.rag.models import DocumentChunk


class RetrievedChunk(BaseModel):
    """A chunk paired with a retrieval score."""

    chunk: DocumentChunk
    score: float


class Retriever(Protocol):
    """Port for a vector, hybrid, or lexical retrieval implementation."""

    def retrieve(
        self,
        chunks: list[DocumentChunk],
        query: str,
        *,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        """Return the most relevant chunks."""


class LexicalRetriever:
    """Small local baseline useful before an embedding store is selected."""

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
