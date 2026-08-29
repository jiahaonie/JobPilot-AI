"""RAG data contracts."""

from pydantic import BaseModel, Field


class ParsedDocument(BaseModel):
    """Normalized document text before chunking."""

    document_id: str
    source_name: str
    text: str


class DocumentChunk(BaseModel):
    """A retrievable text segment with source metadata."""

    document_id: str
    source_name: str
    chunk_index: int
    text: str
    metadata: dict[str, str] = Field(default_factory=dict)


class Citation(BaseModel):
    """Source information returned alongside a generated answer."""

    document_id: str
    source_name: str
    chunk_index: int
    excerpt: str
