"""知识库 API 契约。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import DocumentStatus


class KnowledgeDocumentRead(BaseModel):
    """索引或列表接口返回的文档元数据。"""

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
    """包含原始上传文本的文档元数据。"""

    raw_text: str


class KnowledgeSearchRequest(BaseModel):
    """接口客户端提供的语义搜索参数。"""

    query: str = Field(min_length=1, max_length=2_000)
    top_k: int = Field(default=5, ge=1, le=20)
    max_distance: float | None = Field(default=None, ge=0.0, le=2.0)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        """拒绝只有空白的查询，并保留规范化文本。"""
        normalized = value.strip()
        if not normalized:
            raise ValueError("query cannot be blank")
        return normalized


class KnowledgeSearchResult(BaseModel):
    """一个检索分块及其 Chroma 余弦距离。"""

    chunk_id: str
    document_id: int
    source_name: str
    chunk_index: int
    text: str
    distance: float


class KnowledgeSearchResponse(BaseModel):
    """独立于回答生成返回的已排序分块。"""

    query: str
    max_distance: float
    results: list[KnowledgeSearchResult] = Field(default_factory=list)


class KnowledgeAskRequest(BaseModel):
    """有依据问答的参数。"""

    question: str = Field(min_length=1, max_length=2_000)
    top_k: int = Field(default=5, ge=1, le=20)
    max_distance: float | None = Field(default=None, ge=0.0, le=2.0)

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        """拒绝只有空白的问题。"""
        normalized = value.strip()
        if not normalized:
            raise ValueError("question cannot be blank")
        return normalized


class GroundedAnswerDraft(BaseModel):
    """引用校验前的结构化 LLM 输出。"""

    answer: str = Field(min_length=1)
    cited_chunk_ids: list[str] = Field(min_length=1)


class KnowledgeAskResponse(BaseModel):
    """有证据依据的回答或明确拒答。"""

    answer: str
    refused: bool
    cited_chunk_ids: list[str] = Field(default_factory=list)
    citations: list[KnowledgeSearchResult] = Field(default_factory=list)
