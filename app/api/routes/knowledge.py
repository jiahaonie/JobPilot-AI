"""Knowledge-base HTTP endpoints."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from app.api.dependencies import (
    get_knowledge_document_management_service,
    get_knowledge_document_service,
    get_knowledge_search_service,
)
from app.core.config import Settings, get_settings
from app.schemas.knowledge import (
    KnowledgeDocumentDetail,
    KnowledgeDocumentRead,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from app.services.knowledge import (
    KnowledgeDocumentManagementService,
    KnowledgeDocumentService,
)
from app.services.search import KnowledgeSearchService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

_CONTENT_TYPES_BY_SUFFIX = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
}


@router.get("/documents", response_model=list[KnowledgeDocumentRead])
def list_knowledge_documents(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    service: KnowledgeDocumentManagementService = Depends(
        get_knowledge_document_management_service
    ),
) -> list[KnowledgeDocumentRead]:
    """List indexed documents and their lifecycle states."""

    return service.list_documents(offset=offset, limit=limit)


@router.get("/documents/{document_id}", response_model=KnowledgeDocumentDetail)
def get_knowledge_document(
    document_id: int,
    service: KnowledgeDocumentManagementService = Depends(
        get_knowledge_document_management_service
    ),
) -> KnowledgeDocumentDetail:
    """Return one document including its original uploaded text."""

    return service.get(document_id)


@router.post(
    "/documents",
    response_model=KnowledgeDocumentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_knowledge_document(
    file: Annotated[UploadFile, File(description="UTF-8 TXT or Markdown document")],
    service: KnowledgeDocumentService = Depends(get_knowledge_document_service),
    settings: Settings = Depends(get_settings),
) -> KnowledgeDocumentRead:
    """Validate an uploaded text document and index it into the knowledge base."""

    source_name = Path(file.filename or "").name.strip()
    if not source_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="uploaded file must have a name",
        )

    suffix = Path(source_name).suffix.lower()
    content_type = _CONTENT_TYPES_BY_SUFFIX.get(suffix)
    if content_type is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="only .txt, .md, and .markdown files are supported",
        )

    content = file.file.read(settings.rag_max_upload_bytes + 1)
    if len(content) > settings.rag_max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"file exceeds {settings.rag_max_upload_bytes} bytes",
        )

    try:
        raw_text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="file must be valid UTF-8 text",
        ) from exc

    if not raw_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="document text cannot be empty",
        )

    return service.create(
        source_name=source_name,
        content_type=content_type,
        raw_text=raw_text,
    )


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_knowledge_document(
    document_id: int,
    service: KnowledgeDocumentManagementService = Depends(
        get_knowledge_document_management_service
    ),
) -> None:
    """Delete one document and all of its Chroma chunks."""

    service.delete(document_id)


@router.post("/search", response_model=KnowledgeSearchResponse)
def search_knowledge(
    payload: KnowledgeSearchRequest,
    service: KnowledgeSearchService = Depends(get_knowledge_search_service),
) -> KnowledgeSearchResponse:
    """Return Top-K semantic matches after cosine-distance filtering."""

    return service.search(
        query=payload.query,
        top_k=payload.top_k,
        max_distance=payload.max_distance,
    )
