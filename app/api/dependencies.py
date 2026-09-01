"""FastAPI dependency wiring."""
from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from app.agents.handlers import build_real_tool_specs
from app.agents.orchestrator import ToolRegistry
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.llm.client import StructuredLLMClient, UnavailableLLMClient
from app.llm.deepseek_client import DeepSeekStructuredClient
from app.rag.chunking import TextChunker
from app.rag.embedding import FastEmbedder
from app.rag.parser import PlainTextParser
from app.rag.vector_store import ChromaVectorIndex
from app.services.agent import AgentWorkflowService
from app.services.analysis import JobAnalysisService
from app.services.job import JobService
from app.services.knowledge import (
    KnowledgeDocumentManagementService,
    KnowledgeDocumentService,
)
from app.services.matching import MatchService
from app.services.qa import GroundedQuestionAnsweringService
from app.services.requirements import JobRequirementService
from app.services.resume import ResumeAnalysisService, ResumeService
from app.services.resume_file import ResumeFileService
from app.services.search import KnowledgeSearchService


def get_job_service(db: Session = Depends(get_db)) -> JobService:
    """Build the job service for one request."""

    return JobService(db)


def get_llm_client(
    settings: Settings = Depends(get_settings),
) -> StructuredLLMClient:
    """Build the configured LLM client, or an explicit unavailable placeholder."""

    if not settings.llm_api_key:
        return UnavailableLLMClient()
    return DeepSeekStructuredClient(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        timeout_seconds=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
    )


def get_resume_service(
    db: Session = Depends(get_db),
) -> ResumeService:
    """Build resume storage without requiring an LLM provider."""

    return ResumeService(db)


def get_resume_analysis_service(
    db: Session = Depends(get_db),
    client: StructuredLLMClient = Depends(get_llm_client),
) -> ResumeAnalysisService:
    """Build independently triggered resume skill analysis."""

    return ResumeAnalysisService(db, client)


def get_resume_file_service(
    settings: Settings = Depends(get_settings),
) -> ResumeFileService:
    """Build bounded TXT, Markdown, and electronic PDF extraction."""

    return ResumeFileService(
        max_upload_bytes=settings.resume_max_upload_bytes,
        max_pdf_pages=settings.resume_max_pdf_pages,
        max_text_chars=settings.resume_max_text_chars,
    )


def get_match_service(db: Session = Depends(get_db)) -> MatchService:
    """Build the match service for one request."""

    return MatchService(db)


def get_job_analysis_service(
    db: Session = Depends(get_db),
    client: StructuredLLMClient = Depends(get_llm_client),
) -> JobAnalysisService:
    """Build the job analysis service for one request."""

    return JobAnalysisService(db, client)


def get_job_requirement_service(
    db: Session = Depends(get_db),
) -> JobRequirementService:
    """Build read-only access to previously analyzed job requirements."""

    return JobRequirementService(db)


@lru_cache
def build_embedder(model_name: str) -> FastEmbedder:
    """复用已经加载的 Embedding 模型"""

    return FastEmbedder(model_name=model_name)


@lru_cache
def build_vector_index(
    path: str,
    collection_name: str,
) -> ChromaVectorIndex:
    """复用 Chroma 客户端与集合"""

    return ChromaVectorIndex(
        path=path,
        collection_name=collection_name,
    )


def get_knowledge_document_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> KnowledgeDocumentService:
    """组装文档入库需要的全部组件。"""

    return KnowledgeDocumentService(
        session=db,
        parser=PlainTextParser(),
        chunker=TextChunker(
            chunk_size=settings.rag_chunk_size,
            overlap=settings.rag_chunk_overlap,
        ),
        embedder=build_embedder(settings.rag_embedding_model),
        vector_index=build_vector_index(
            settings.rag_chroma_path,
            settings.rag_collection_name,
        ),
    )


def get_knowledge_document_management_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> KnowledgeDocumentManagementService:
    """Build document management without loading the embedding model."""

    return KnowledgeDocumentManagementService(
        session=db,
        vector_index=build_vector_index(
            settings.rag_chroma_path,
            settings.rag_collection_name,
        ),
    )


def get_knowledge_search_service(
    settings: Settings = Depends(get_settings),
) -> KnowledgeSearchService:
    """Build semantic retrieval with the same embedding/index pair as ingestion."""

    return KnowledgeSearchService(
        embedder=build_embedder(settings.rag_embedding_model),
        vector_index=build_vector_index(
            settings.rag_chroma_path,
            settings.rag_collection_name,
        ),
        default_max_distance=settings.rag_max_distance,
    )


def get_grounded_qa_service(
    search_service: KnowledgeSearchService = Depends(get_knowledge_search_service),
    client: StructuredLLMClient = Depends(get_llm_client),
) -> GroundedQuestionAnsweringService:
    """Build grounded QA from retrieval plus the configured structured LLM."""

    return GroundedQuestionAnsweringService(
        search_service=search_service,
        client=client,
    )


def get_agent_workflow_service(
    db: Session = Depends(get_db),
    client: StructuredLLMClient = Depends(get_llm_client),
    search_service: KnowledgeSearchService = Depends(get_knowledge_search_service),
) -> AgentWorkflowService:
    """Bind the model selector to three real application handlers."""

    registry = ToolRegistry(
        build_real_tool_specs(session=db, search_service=search_service)
    )
    return AgentWorkflowService(client=client, registry=registry)
