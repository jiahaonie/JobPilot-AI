"""检索增强生成数据契约。"""

from pydantic import BaseModel, Field


class ParsedDocument(BaseModel):
    """分块前的规范化文档文本。"""

    document_id: str
    source_name: str
    text: str


class DocumentChunk(BaseModel):
    """带来源元数据的可检索文本片段。"""

    document_id: str
    source_name: str
    chunk_index: int
    text: str
    metadata: dict[str, str] = Field(default_factory=dict)
