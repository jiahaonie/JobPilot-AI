"""Vector-index port and Chroma adapter."""

from typing import Any, Protocol

import chromadb
from pydantic import BaseModel

from app.rag.models import DocumentChunk


class ChromaCollection(Protocol):
    """Subset of a Chroma collection used by the application."""

    def upsert(
        self,
        *,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        """Create or replace chunk records."""

    def query(
        self,
        *,
        query_embeddings: list[list[float]],
        n_results: int,
        include: list[str],
    ) -> dict[str, Any]:
        """Return nearest records for a batch of query vectors."""

    def delete(self, *, where: dict[str, Any]) -> None:
        """Delete records matching metadata."""


class VectorSearchResult(BaseModel):
    """One Chroma match with its cosine distance."""

    chunk_id: str
    chunk: DocumentChunk
    distance: float


class VectorIndex(Protocol):
    """Application-facing vector persistence boundary."""

    def upsert(
        self,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
    ) -> None:
        """Persist chunks and their precomputed embeddings."""

    def query(
        self,
        query_embedding: list[float],
        *,
        top_k: int = 5,
    ) -> list[VectorSearchResult]:
        """Return the nearest stored chunks."""

    def delete_document(self, document_id: str) -> None:
        """Delete every chunk belonging to one source document."""


class ChromaVectorIndex:
    """Store precomputed vectors and chunk text in a Chroma collection."""

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
        """Write parallel chunk fields using deterministic IDs."""

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
    ) -> list[VectorSearchResult]:
        """Map Chroma's first query batch back into domain objects."""

        if not query_embedding or top_k <= 0:
            return []

        payload = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        return self._map_first_batch(payload)

    def delete_document(self, document_id: str) -> None:
        """Delete all vectors associated with one SQLite document."""

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
