"""Citation construction."""

from app.rag.models import Citation
from app.rag.retrieval import RetrievedChunk


def build_citations(candidates: list[RetrievedChunk]) -> list[Citation]:
    """Convert retrieved chunks into source references for an answer."""

    return [
        Citation(
            document_id=item.chunk.document_id,
            source_name=item.chunk.source_name,
            chunk_index=item.chunk.chunk_index,
            excerpt=item.chunk.text,
        )
        for item in candidates
    ]
