"""知识文档持久化操作。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import DocumentStatus
from app.models.knowledge_document import KnowledgeDocument


class KnowledgeDocumentRepository:
    """封装知识文档元数据的 SQLAlchemy 查询。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, document: KnowledgeDocument) -> KnowledgeDocument:
        """暂存文档并填充数据库生成的编号。"""
        self.session.add(document)
        self.session.flush()
        return document

    def get(self, document_id: int) -> KnowledgeDocument | None:
        """按主键查找文档。"""
        return self.session.get(KnowledgeDocument, document_id)

    def list_documents(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[KnowledgeDocument]:
        """按从新到旧顺序返回文档。"""
        statement = (
            select(KnowledgeDocument)
            .order_by(
                KnowledgeDocument.created_at.desc(),
                KnowledgeDocument.id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def list_ready(self) -> list[KnowledgeDocument]:
        """返回已有可检索分块的文档。"""
        statement = (
            select(KnowledgeDocument)
            .where(KnowledgeDocument.status == DocumentStatus.READY)
            .order_by(KnowledgeDocument.created_at.desc())
        )
        return list(self.session.scalars(statement))

    def delete(self, document: KnowledgeDocument) -> None:
        """暂存知识文档删除操作。"""
        self.session.delete(document)
