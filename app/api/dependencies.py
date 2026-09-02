"""应用的 FastAPI 依赖装配。"""

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
from app.services.match_report import MatchReportService
from app.services.matching import MatchService
from app.services.qa import GroundedQuestionAnsweringService
from app.services.requirements import JobRequirementService
from app.services.resume import ResumeAnalysisService, ResumeService
from app.services.resume_file import ResumeFileService
from app.services.search import KnowledgeSearchService


def get_job_service(db: Session = Depends(get_db)) -> JobService:
    """为单次请求构建岗位服务。"""
    return JobService(db)


def get_llm_client(
    settings: Settings = Depends(get_settings),
) -> StructuredLLMClient:
    """构建已配置的 LLM 客户端，未配置时返回明确的不可用占位实现。"""
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
    """构建不依赖 LLM 服务商的简历存储服务。"""
    return ResumeService(db)


def get_resume_analysis_service(
    db: Session = Depends(get_db),
    client: StructuredLLMClient = Depends(get_llm_client),
) -> ResumeAnalysisService:
    """构建可独立触发的简历技能分析服务。"""
    return ResumeAnalysisService(db, client)


def get_resume_file_service(
    settings: Settings = Depends(get_settings),
) -> ResumeFileService:
    """构建受限的 TXT、Markdown 和电子 PDF 提取服务。"""
    return ResumeFileService(
        max_upload_bytes=settings.resume_max_upload_bytes,
        max_pdf_pages=settings.resume_max_pdf_pages,
        max_text_chars=settings.resume_max_text_chars,
    )


def get_match_service(db: Session = Depends(get_db)) -> MatchService:
    """为单次请求构建匹配服务。"""
    return MatchService(db)


def get_match_report_service(
    db: Session = Depends(get_db),
) -> MatchReportService:
    """为单次请求构建匹配报告持久化服务。"""
    return MatchReportService(db)


def get_job_analysis_service(
    db: Session = Depends(get_db),
    client: StructuredLLMClient = Depends(get_llm_client),
) -> JobAnalysisService:
    """为单次请求构建岗位分析服务。"""
    return JobAnalysisService(db, client)


def get_job_requirement_service(
    db: Session = Depends(get_db),
) -> JobRequirementService:
    """构建对已分析岗位要求的只读访问服务。"""
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
    """构建无需加载嵌入模型的文档管理服务。"""
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
    """使用与入库相同的嵌入和索引组件构建语义检索。"""
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
    """结合检索与结构化 LLM 构建有依据的问答服务。"""
    return GroundedQuestionAnsweringService(
        search_service=search_service,
        client=client,
    )


def get_agent_workflow_service(
    db: Session = Depends(get_db),
    client: StructuredLLMClient = Depends(get_llm_client),
    search_service: KnowledgeSearchService = Depends(get_knowledge_search_service),
) -> AgentWorkflowService:
    """将模型选择器绑定到三个真实应用处理器。"""
    registry = ToolRegistry(build_real_tool_specs(session=db, search_service=search_service))
    return AgentWorkflowService(client=client, registry=registry)
