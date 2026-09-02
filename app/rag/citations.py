"""引用构建。"""

from app.rag.models import Citation
from app.rag.retrieval import RetrievedChunk


def build_citations(candidates: list[RetrievedChunk]) -> list[Citation]:
    """将检索分块转换为回答的来源引用。"""
    return [
        Citation(
            document_id=item.chunk.document_id,
            source_name=item.chunk.source_name,
            chunk_index=item.chunk.chunk_index,
            excerpt=item.chunk.text,
        )
        for item in candidates
    ]
