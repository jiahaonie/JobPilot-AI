"""应用配置与环境变量加载。"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_builtin_document_ids(value: str) -> list[int]:
    """将逗号分隔配置转换为保序、去重的正整数编号。"""
    document_ids: list[int] = []
    for item in value.split(","):
        normalized = item.strip()
        if not normalized:
            continue
        if not normalized.isdigit() or int(normalized) < 1:
            return []
        document_id = int(normalized)
        if document_id not in document_ids:
            document_ids.append(document_id)
    return document_ids


class Settings(BaseSettings):
    """应用组合根共享的运行时配置。"""

    app_name: str = "JobPilot AI"
    environment: Literal["development", "test", "staging", "production"] = "development"
    debug: bool = False
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./jobpilot.db"
    auto_create_tables: bool = False

    llm_provider: str = "deepseek"
    llm_api_key: str | None = None
    llm_model: str = "deepseek-chat"
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_timeout_seconds: float = 30.0
    llm_max_retries: int = 2
    llm_max_tokens: int = 4096
    llm_thinking_enabled: bool = False

    rag_chroma_path: str = "./data/chroma"
    rag_collection_name: str = "jobpilot_knowledge"
    rag_builtin_collection_name: str = "jobpilot_builtin_knowledge"
    rag_builtin_document_ids: str = ""
    rag_embedding_model: str = "BAAI/bge-small-zh-v1.5"
    rag_chunk_size: int = 500
    rag_chunk_overlap: int = 80
    rag_max_upload_bytes: int = 2 * 1024 * 1024
    rag_max_distance: float = 0.45
    rag_answer_top_k: int = 5
    rag_plan_top_k: int = 5
    rag_plan_context_chars: int = 30_000
    rag_plan_prompt_version: str = "study-plan-rag-v1"
    rag_plan_time_budget_seconds: float = 120.0

    resume_max_upload_bytes: int = 5 * 1024 * 1024
    resume_max_pdf_pages: int = 20
    resume_max_text_chars: int = 100_000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """返回进程级配置实例。"""
    return Settings()
