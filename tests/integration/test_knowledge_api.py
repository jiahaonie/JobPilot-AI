"""HTTP tests for knowledge-document uploads."""

from datetime import UTC, datetime

from app.api.dependencies import (
    get_knowledge_document_management_service,
    get_knowledge_document_service,
)
from app.core.config import Settings, get_settings
from app.models.enums import DocumentStatus
from app.schemas.knowledge import KnowledgeDocumentDetail, KnowledgeDocumentRead


class RecordingKnowledgeService:
    """Record validated upload fields without loading a real embedding model."""

    def __init__(self) -> None:
        self.create_calls: list[dict[str, str]] = []
        self.list_calls: list[tuple[int, int]] = []
        self.get_calls: list[int] = []
        self.delete_calls: list[int] = []

    @staticmethod
    def document() -> KnowledgeDocumentDetail:
        now = datetime.now(UTC)
        return KnowledgeDocumentDetail(
            id=7,
            source_name="notes.md",
            content_type="text/markdown",
            status=DocumentStatus.READY,
            chunk_count=1,
            error_message=None,
            created_at=now,
            updated_at=now,
            raw_text="# FastAPI\n\n依赖注入。",
        )

    def create(
        self,
        *,
        source_name: str,
        content_type: str,
        raw_text: str,
    ) -> KnowledgeDocumentRead:
        self.create_calls.append(
            {
                "source_name": source_name,
                "content_type": content_type,
                "raw_text": raw_text,
            }
        )
        now = datetime.now(UTC)
        return KnowledgeDocumentRead(
            id=7,
            source_name=source_name,
            content_type=content_type,
            status=DocumentStatus.READY,
            chunk_count=1,
            error_message=None,
            created_at=now,
            updated_at=now,
        )

    def list_documents(
        self,
        *,
        offset: int,
        limit: int,
    ) -> list[KnowledgeDocumentRead]:
        self.list_calls.append((offset, limit))
        return [self.document()]

    def get(self, document_id: int) -> KnowledgeDocumentDetail:
        self.get_calls.append(document_id)
        return self.document()

    def delete(self, document_id: int) -> None:
        self.delete_calls.append(document_id)


def test_uploads_utf8_markdown_document(application, client) -> None:
    service = RecordingKnowledgeService()
    application.dependency_overrides[get_knowledge_document_service] = lambda: service

    response = client.post(
        "/api/v1/knowledge/documents",
        files={"file": ("notes.md", "# FastAPI\n\n依赖注入。".encode(), "text/markdown")},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "ready"
    assert service.create_calls == [
        {
            "source_name": "notes.md",
            "content_type": "text/markdown",
            "raw_text": "# FastAPI\n\n依赖注入。",
        }
    ]


def test_rejects_unsupported_file_extension(application, client) -> None:
    service = RecordingKnowledgeService()
    application.dependency_overrides[get_knowledge_document_service] = lambda: service

    response = client.post(
        "/api/v1/knowledge/documents",
        files={"file": ("notes.pdf", b"not a PDF", "application/pdf")},
    )

    assert response.status_code == 415
    assert service.create_calls == []


def test_rejects_non_utf8_document(application, client) -> None:
    service = RecordingKnowledgeService()
    application.dependency_overrides[get_knowledge_document_service] = lambda: service

    response = client.post(
        "/api/v1/knowledge/documents",
        files={"file": ("notes.txt", b"\xff\xfe", "text/plain")},
    )

    assert response.status_code == 422
    assert service.create_calls == []


def test_rejects_document_larger_than_configured_limit(application, client) -> None:
    service = RecordingKnowledgeService()
    application.dependency_overrides[get_knowledge_document_service] = lambda: service
    application.dependency_overrides[get_settings] = lambda: Settings(
        environment="test",
        rag_max_upload_bytes=4,
    )

    response = client.post(
        "/api/v1/knowledge/documents",
        files={"file": ("notes.txt", b"12345", "text/plain")},
    )

    assert response.status_code == 413
    assert service.create_calls == []


def test_rejects_empty_document(application, client) -> None:
    service = RecordingKnowledgeService()
    application.dependency_overrides[get_knowledge_document_service] = lambda: service

    response = client.post(
        "/api/v1/knowledge/documents",
        files={"file": ("notes.txt", b" \n\t", "text/plain")},
    )

    assert response.status_code == 422
    assert service.create_calls == []


def test_lists_and_gets_knowledge_documents(application, client) -> None:
    service = RecordingKnowledgeService()
    application.dependency_overrides[get_knowledge_document_management_service] = (
        lambda: service
    )

    list_response = client.get(
        "/api/v1/knowledge/documents",
        params={"offset": 0, "limit": 20},
    )
    detail_response = client.get("/api/v1/knowledge/documents/7")

    assert list_response.status_code == 200
    assert list_response.json()[0]["source_name"] == "notes.md"
    assert service.list_calls == [(0, 20)]
    assert detail_response.status_code == 200
    assert detail_response.json()["raw_text"] == "# FastAPI\n\n依赖注入。"
    assert service.get_calls == [7]


def test_deletes_knowledge_document(application, client) -> None:
    service = RecordingKnowledgeService()
    application.dependency_overrides[get_knowledge_document_management_service] = (
        lambda: service
    )

    response = client.delete("/api/v1/knowledge/documents/7")

    assert response.status_code == 204
    assert service.delete_calls == [7]
