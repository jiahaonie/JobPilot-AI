from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundError
from app.models.enums import DocumentStatus
from app.models.knowledge_document import KnowledgeDocument
from app.rag.chunking import TextChunker
from app.rag.embedding import Embedder
from app.rag.parser import PlainTextParser
from app.rag.vector_store import VectorIndex
from app.repositories.knowledge_document import KnowledgeDocumentRepository


class KnowledgeDocumentManagementService:
    """在不加载嵌入模型的情况下管理已持久化文档。"""

    def __init__(
        self,
        session: Session,
        vector_index: VectorIndex,
    ) -> None:
        self.session = session
        self.vector_index = vector_index
        self.repository = KnowledgeDocumentRepository(session)

    def get(self, document_id: int) -> KnowledgeDocument:
        """返回文档；不存在时抛出领域层未找到异常。"""
        document = self.repository.get(document_id)
        if document is None:
            raise ResourceNotFoundError(f"Knowledge document {document_id} was not found")
        return document

    def list_documents(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[KnowledgeDocument]:
        """返回数量受限的知识文档列表。"""
        return self.repository.list_documents(offset=offset, limit=limit)

    def delete(self, document_id: int) -> None:
        """在同一受管生命周期中从 Chroma 和 SQLite 删除文档。"""
        document = self.get(document_id)
        document.status = DocumentStatus.DELETING
        document.error_message = None
        self.session.commit()

        try:
            self.vector_index.delete_document(str(document.id))
            self.repository.delete(document)
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            remaining_document = self.repository.get(document_id)
            if remaining_document is not None:
                remaining_document.status = DocumentStatus.FAILED
                remaining_document.error_message = f"document deletion failed: {exc}"
                self.session.commit()
            raise


class KnowledgeDocumentService(KnowledgeDocumentManagementService):
    """索引上传文档，并提供共享的管理操作。"""

    def __init__(
        self,
        session: Session,
        parser: PlainTextParser,
        chunker: TextChunker,
        embedder: Embedder,
        vector_index: VectorIndex,
    ) -> None:
        super().__init__(session=session, vector_index=vector_index)
        self.parser = parser
        self.chunker = chunker
        self.embedder = embedder

    def create(
        self,
        *,
        source_name: str,
        content_type: str,
        raw_text: str,
        is_builtin: bool = False,
        approved: bool = False,
        source_sha256: str | None = None,
        content_sha256: str | None = None,
        embedding_model: str | None = None,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> KnowledgeDocument:
        # 1. SQLite 先保存 indexing 状态
        document = KnowledgeDocument(
            source_name=source_name,
            content_type=content_type,
            raw_text=raw_text,
            status=DocumentStatus.INDEXING,
            is_builtin=is_builtin,
            approved=approved,
            source_sha256=source_sha256,
            content_sha256=content_sha256,
            embedding_model=embedding_model,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        self.repository.add(document)
        self.session.commit()
        self.session.refresh(document)

        try:
            # 2.解析与分块
            parsed = self.parser.parse(
                document_id=str(document.id),
                source_name=document.source_name,
                text=document.raw_text,
            )
            chunks = self.chunker.chunk(parsed)

            # 3. 生成向量并写入 Chroma
            embeddings = self.embedder.embed_documents(
                [chunk.text for chunk in chunks],
            )
            self.vector_index.upsert(chunks, embeddings)

            # 4. SQLite 更新为 ready
            document.status = DocumentStatus.READY
            document.chunk_count = len(chunks)
            document.error_message = None
            self.session.commit()
            self.session.refresh(document)
            return document
        except Exception as exc:
            # 撤销当前未提交的 SQLite 修改
            self.session.rollback()

            # 补偿：Chroma 清理失败不能阻止 SQLite 记录失败状态
            cleanup_error: Exception | None = None
            try:
                self.vector_index.delete_document(str(document.id))
            except Exception as cleanup_exc:
                cleanup_error = cleanup_exc

            document.status = DocumentStatus.FAILED
            document.chunk_count = 0
            document.error_message = str(exc)
            if cleanup_error is not None:
                document.error_message += f"; vector cleanup failed: {cleanup_error}"
            self.session.commit()

            # 保留最初的入库异常，不让清理异常覆盖它
            raise
