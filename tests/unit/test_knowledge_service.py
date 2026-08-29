import pytest

from app.core.exceptions import ResourceNotFoundError
from app.models.enums import DocumentStatus
from app.models.knowledge_document import KnowledgeDocument
from app.rag.chunking import TextChunker
from app.rag.models import DocumentChunk
from app.rag.parser import PlainTextParser
from app.repositories.knowledge_document import KnowledgeDocumentRepository
from app.services.knowledge import KnowledgeDocumentService


class FailingEmbedder:
    """模拟 Embedding 服务失败"""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("embedding failed")


class RecordingEmbedder:
    """记录收到的文本，并返回固定向量。"""

    def __init__(self) -> None:
        self.received_texts: list[str] = []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.received_texts = texts
        return [[0.1, 0.2] for _ in texts]


class RecordingVectorIndex:
    """记录 Service 对 Chroma 的写入与清理。"""

    def __init__(self) -> None:
        self.upsert_calls: list[
            tuple[list[DocumentChunk], list[list[float]]]
        ] = []
        self.deleted_document_ids: list[str] = []

    def upsert(
        self,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
    ) -> None:
        self.upsert_calls.append((chunks, embeddings))

    def delete_document(self, document_id: str) -> None:
        self.deleted_document_ids.append(document_id)


class CleanupFailingVectorIndex(RecordingVectorIndex):
    """记录清理调用，并模拟 Chroma 清理失败。"""

    def delete_document(self, document_id: str) -> None:
        super().delete_document(document_id)
        raise RuntimeError("vector cleanup failed")


def add_document(
    session,
    *,
    source_name: str = "notes.txt",
    status: DocumentStatus = DocumentStatus.READY,
) -> KnowledgeDocument:
    """Persist one document for management-use-case tests."""

    document = KnowledgeDocument(
        source_name=source_name,
        content_type="text/plain",
        raw_text=f"content from {source_name}",
        status=status,
        chunk_count=1,
    )
    KnowledgeDocumentRepository(session).add(document)
    session.commit()
    session.refresh(document)
    return document


def test_create_marks_document_failed_when_embedding_fails(
    application,
    client,
) -> None:
    vector_index = RecordingVectorIndex()

    with application.state.database.session() as session:
        service = KnowledgeDocumentService(
            session=session,
            parser=PlainTextParser(),
            chunker=TextChunker(),
            embedder=FailingEmbedder(),
            vector_index=vector_index,
        )

        # 执行：确认 Service 会继续抛出原异常
        with pytest.raises(RuntimeError, match="embedding failed"):
            service.create(
                source_name="notes.txt",
                content_type="text/plain",
                raw_text="FastAPI 使用依赖注入",
            )

        # 验证 SQLite 状态
        documents = KnowledgeDocumentRepository(session).list_documents()
        assert len(documents) == 1

        document = documents[0]
        assert document.status == DocumentStatus.FAILED
        assert document.chunk_count == 0
        assert document.error_message == "embedding failed"

        # 验证 Chroma 补偿清理
        assert vector_index.upsert_calls == []
        assert vector_index.deleted_document_ids == [str(document.id)]


def test_create_marks_failed_when_vector_cleanup_also_fails(
    application,
    client,
) -> None:
    vector_index = CleanupFailingVectorIndex()

    with application.state.database.session() as session:
        service = KnowledgeDocumentService(
            session=session,
            parser=PlainTextParser(),
            chunker=TextChunker(),
            embedder=FailingEmbedder(),
            vector_index=vector_index,
        )

        # 清理失败不能覆盖最初的入库异常。
        with pytest.raises(RuntimeError, match="embedding failed"):
            service.create(
                source_name="notes.txt",
                content_type="text/plain",
                raw_text="FastAPI 使用依赖注入",
            )

        documents = KnowledgeDocumentRepository(session).list_documents()
        assert len(documents) == 1

        document = documents[0]
        assert document.status == DocumentStatus.FAILED
        assert document.chunk_count == 0
        assert document.error_message is not None
        assert "embedding failed" in document.error_message
        assert "vector cleanup failed" in document.error_message
        assert vector_index.deleted_document_ids == [str(document.id)]


def test_create_indexes_document_and_marks_ready(
    application,
    client,
) -> None:
    embedder = RecordingEmbedder()
    vector_index = RecordingVectorIndex()

    with application.state.database.session() as session:
        service = KnowledgeDocumentService(
            session=session,
            parser=PlainTextParser(),
            chunker=TextChunker(),
            embedder=embedder,
            vector_index=vector_index,
        )

        document = service.create(
            source_name="notes.txt",
            content_type="text/plain",
            raw_text="FastAPI 使用依赖注入。",
        )

        stored_document = KnowledgeDocumentRepository(session).get(document.id)
        assert stored_document is not None
        assert stored_document.status == DocumentStatus.READY
        assert stored_document.chunk_count == 1
        assert stored_document.error_message is None

        assert embedder.received_texts == ["FastAPI 使用依赖注入。"]
        assert len(vector_index.upsert_calls) == 1
        chunks, embeddings = vector_index.upsert_calls[0]
        assert [chunk.text for chunk in chunks] == embedder.received_texts
        assert embeddings == [[0.1, 0.2]]
        assert vector_index.deleted_document_ids == []


def test_list_and_get_documents(application, client) -> None:
    vector_index = RecordingVectorIndex()

    with application.state.database.session() as session:
        first = add_document(session, source_name="first.txt")
        second = add_document(session, source_name="second.txt")
        service = KnowledgeDocumentService(
            session=session,
            parser=PlainTextParser(),
            chunker=TextChunker(),
            embedder=RecordingEmbedder(),
            vector_index=vector_index,
        )

        documents = service.list_documents(offset=0, limit=10)

        assert [document.id for document in documents] == [second.id, first.id]
        assert service.get(first.id).raw_text == "content from first.txt"


def test_get_raises_not_found_for_unknown_document(application, client) -> None:
    with application.state.database.session() as session:
        service = KnowledgeDocumentService(
            session=session,
            parser=PlainTextParser(),
            chunker=TextChunker(),
            embedder=RecordingEmbedder(),
            vector_index=RecordingVectorIndex(),
        )

        with pytest.raises(ResourceNotFoundError, match="999"):
            service.get(999)


def test_delete_removes_chroma_chunks_and_sqlite_document(application, client) -> None:
    vector_index = RecordingVectorIndex()

    with application.state.database.session() as session:
        document = add_document(session)
        service = KnowledgeDocumentService(
            session=session,
            parser=PlainTextParser(),
            chunker=TextChunker(),
            embedder=RecordingEmbedder(),
            vector_index=vector_index,
        )

        service.delete(document.id)

        assert vector_index.deleted_document_ids == [str(document.id)]
        assert KnowledgeDocumentRepository(session).get(document.id) is None


def test_delete_marks_failed_when_chroma_cleanup_fails(application, client) -> None:
    vector_index = CleanupFailingVectorIndex()

    with application.state.database.session() as session:
        document = add_document(session)
        service = KnowledgeDocumentService(
            session=session,
            parser=PlainTextParser(),
            chunker=TextChunker(),
            embedder=RecordingEmbedder(),
            vector_index=vector_index,
        )

        with pytest.raises(RuntimeError, match="vector cleanup failed"):
            service.delete(document.id)

        remaining_document = KnowledgeDocumentRepository(session).get(document.id)
        assert remaining_document is not None
        assert remaining_document.status == DocumentStatus.FAILED
        assert remaining_document.error_message is not None
        assert "document deletion failed" in remaining_document.error_message
        assert "vector cleanup failed" in remaining_document.error_message
