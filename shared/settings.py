from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core
    data_dir: str = "/app/data"
    index_dir: str = "/app/indexes"
    tz: str = "Asia/Ho_Chi_Minh"

    # Data source
    bopd_zip_url: str = ""  # required at runtime, validated on use

    # Embedding
    embedder_backend: str = "builtin"  # builtin | st
    embedder_model: str = "intfloat/multilingual-e5-small"

    # Hybrid search weights
    default_alpha: float = 0.6
    default_beta: float = 0.4

    # RAG
    rag_backend: str = "ollama"  # ollama | summary
    rag_model: str = "qwen2.5:7b"
    rag_max_chars: int = 8000
    ollama_host: str = "http://ollama:11434"

    # RQ / Redis
    redis_host: str = "redis"
    redis_port: int = 6379
    rq_queue: str = "bo_pd_jobs"

    # Updater schedule
    monthly_days: str = "1,16"
    daily_refresh_at: str = "03:30"

    # Optional auth
    auth_enabled: bool = False
    auth_secret: str = "change-me-in-production"

    # Optional rate limiting
    rate_limit_enabled: bool = False
    rate_limit_per_minute: int = 60
    rate_limit_llm_per_minute: int = 10

    source_name: str = (
        "Cổng thông tin điện tử pháp điển: phapdien.moj.gov.vn"
    )

    def validate_required(self) -> None:
        """Call at startup to fail fast on missing required config."""
        if not self.bopd_zip_url:
            raise ValueError("BOPD_ZIP_URL is required but not set")


settings = Settings()
