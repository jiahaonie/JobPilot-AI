"""Knowledge-base API contracts."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import DocumentStatus


class KnowledgeDocumentRead(BaseModel):
    """Document metadata returned after indexing or listing."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    source_name: str
    content_type: str
    status: DocumentStatus
    chunk_count: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class KnowledgeDocumentDetail(KnowledgeDocumentRead):
    """Document metadata plus the original uploaded text."""

    raw_text: str


class KnowledgeSearchRequest(BaseModel):
    """Semantic-search parameters supplied by an API client."""

    query: str = Field(min_length=1, max_length=2_000)
    top_k: int = Field(default=5, ge=1, le=20)
    max_distance: float | None = Field(default=None, ge=0.0, le=2.0)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        """Reject whitespace-only queries and keep the normalized text."""

        normalized = value.strip()
        if not normalized:
            raise ValueError("query cannot be blank")
        return normalized


class KnowledgeSearchResult(BaseModel):
    """One retrieved chunk and its Chroma cosine distance."""

    chunk_id: str
    document_id: int
    source_name: str
    chunk_index: int
    text: str
    distance: float


class KnowledgeSearchResponse(BaseModel):
    """Ranked chunks returned independently of answer generation."""

    query: str
    max_distance: float
    results: list[KnowledgeSearchResult] = Field(default_factory=list)


class KnowledgeAskRequest(BaseModel):
    """Grounded question-answering parameters."""

    question: str = Field(min_length=1, max_length=2_000)
    top_k: int = Field(default=5, ge=1, le=20)
    max_distance: float | None = Field(default=None, ge=0.0, le=2.0)

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        """Reject whitespace-only questions."""

        normalized = value.strip()
        if not normalized:
            raise ValueError("question cannot be blank")
        return normalized


class GroundedAnswerDraft(BaseModel):
    """Structured LLM output before citation validation."""

    answer: str = Field(min_length=1)
    cited_chunk_ids: list[str] = Field(min_length=1)


class KnowledgeAskResponse(BaseModel):
    """An evidence-grounded answer or an explicit refusal."""

    answer: str
    refused: bool
    cited_chunk_ids: list[str] = Field(default_factory=list)
    citations: list[KnowledgeSearchResult] = Field(default_factory=list)
