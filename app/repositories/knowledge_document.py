"""Persistence operations for knowledge documents."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import DocumentStatus
from app.models.knowledge_document import KnowledgeDocument


class KnowledgeDocumentRepository:
    """Encapsulate SQLAlchemy queries for knowledge-document metadata."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, document: KnowledgeDocument) -> KnowledgeDocument:
        """Stage a document and populate its database-generated ID."""

        self.session.add(document)
        self.session.flush()
        return document

    def get(self, document_id: int) -> KnowledgeDocument | None:
        """Find a document by its primary key."""

        return self.session.get(KnowledgeDocument, document_id)

    def list_documents(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[KnowledgeDocument]:
        """Return documents ordered from newest to oldest."""

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
        """Return documents whose chunks are available for retrieval."""

        statement = (
            select(KnowledgeDocument)
            .where(KnowledgeDocument.status == DocumentStatus.READY)
            .order_by(KnowledgeDocument.created_at.desc())
        )
        return list(self.session.scalars(statement))

    def delete(self, document: KnowledgeDocument) -> None:
        """Stage a knowledge-document deletion."""

        self.session.delete(document)
