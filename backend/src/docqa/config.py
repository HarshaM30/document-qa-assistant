"""Typed application settings, read from environment variables and the repo-level `.env`."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_repo_root() -> Path:
    """Repo root: `DOCQA_ROOT` if set, else three levels above this package (backend/src/docqa)."""
    override = os.environ.get("DOCQA_ROOT")
    if override:
        return Path(override).resolve()
    return Path(__file__).resolve().parents[3]


REPO_ROOT = _find_repo_root()

SEC_USER_AGENT_PLACEHOLDER = "Your Name your.email@example.com"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    app_env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    frontend_origin: str = "http://localhost:5173"

    # --- Datastores ---
    database_url: str = "postgresql+asyncpg://docqa:change-me@localhost:5434/docqa"
    test_database_url: str = "postgresql+asyncpg://docqa:change-me@localhost:5434/docqa_test"
    db_pool_size: int = 5
    db_max_overflow: int = 5
    redis_url: str = "redis://localhost:6380/0"
    test_redis_url: str = "redis://localhost:6380/1"

    # --- Auth / sessions ---
    session_secret_key: SecretStr = SecretStr("dev-only-insecure-session-key")
    session_cookie_name: str = "docqa_session"
    session_cookie_secure: bool = False
    session_ttl_hours: int = 168

    # --- LLM (used from Milestone 3) ---
    llm_provider: str = "groq"
    llm_model: str = "openai/gpt-oss-120b"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 1024
    llm_timeout_seconds: float = 60
    llm_reasoning_effort: str = "low"
    groq_api_key: SecretStr = SecretStr("")
    judge_provider: str = "groq"
    judge_model: str = "qwen/qwen3.8-27b"

    # --- Embeddings / reranker ---
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384
    embedding_batch_size: int = 32
    embedding_threads: int | None = 2
    reranker_model: str = "Xenova/ms-marco-MiniLM-L-6-v2"
    fastembed_cache_dir: Path = Path(".cache/fastembed")

    # --- Chunking / retrieval ---
    chunk_size_tokens: int = 512
    chunk_overlap_tokens: int = 64
    retrieval_vector_top_k: int = 30
    retrieval_keyword_top_k: int = 30
    rrf_k: int = 60
    rerank_enabled: bool = True
    rerank_top_n: int = 6
    refusal_min_rerank_score: float = 0.0

    # --- Rate limiting ---
    rate_limit_questions_per_minute: int = 5
    rate_limit_questions_per_day: int = 100

    # --- Uploads / worker ---
    upload_dir: Path = Path("data/uploads")
    max_upload_mb: int = 25
    worker_max_jobs: int = 2
    worker_job_timeout_seconds: int = 1800
    ingest_max_retries: int = 3
    ingest_retry_base_delay_seconds: float = 5.0

    # --- SEC EDGAR ---
    sec_user_agent: str = ""
    sec_filings_per_company: int = 3
    sec_max_requests_per_second: float = Field(default=5, gt=0, lt=10)
    raw_data_dir: Path = Path("data/raw")
    companies_file: Path = Path("data/companies.yaml")
    filings_lock_file: Path = Path("data/filings.lock.json")

    @field_validator(
        "fastembed_cache_dir",
        "upload_dir",
        "raw_data_dir",
        "companies_file",
        "filings_lock_file",
    )
    @classmethod
    def _resolve_against_repo_root(cls, value: Path) -> Path:
        return value if value.is_absolute() else REPO_ROOT / value

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def sec_user_agent_is_set(self) -> bool:
        ua = self.sec_user_agent.strip()
        return bool(ua) and ua != SEC_USER_AGENT_PLACEHOLDER and "example.com" not in ua


@lru_cache
def get_settings() -> Settings:
    return Settings()
