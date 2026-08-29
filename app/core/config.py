"""Application configuration and environment loading."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings shared by the application composition root."""

    app_name: str = "JobPilot AI"
    environment: Literal["development", "test", "staging", "production"] = "development"
    debug: bool = False
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./jobpilot.db"
    auto_create_tables: bool = True

    llm_provider: str = "deepseek"
    llm_api_key: str | None = None
    llm_model: str = "deepseek-chat"
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_timeout_seconds: float = 30.0
    llm_max_retries: int = 2

    rag_chroma_path: str = "./data/chroma"
    rag_collection_name: str = "jobpilot_knowledge"
    rag_embedding_model: str = "BAAI/bge-small-zh-v1.5"
    rag_chunk_size: int = 500
    rag_chunk_overlap: int = 80
    rag_max_upload_bytes: int = 2 * 1024 * 1024
    rag_max_distance: float = 0.45
    rag_answer_top_k: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance."""

    return Settings()
