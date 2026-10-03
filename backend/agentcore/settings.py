"""Centralized configuration for the agentcore multi-agent system.

A single ``AgentCoreSettings`` object is the source of truth for every
subsystem the rebuild introduces (LLM providers now; Postgres, Redis,
RabbitMQ, Pinecone, security, and observability in later tasks). Fields for
not-yet-built subsystems are declared up front with sensible defaults so
each task only has to *read* settings, never re-plumb how they're loaded.

Values are read from environment variables and from ``backend/.env`` (via
pydantic-settings), matching the convention already used by
``backend/.env.example`` — existing GEMINI_*/OLLAMA_* keys work unchanged.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve to backend/.env by file location, not process CWD, so settings load
# correctly whether the app is started from backend/ (per README) or tests
# are run from the repo root.
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class AgentCoreSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # -- General -----------------------------------------------------------
    environment: str = Field(default="development", description="development|staging|production")
    debug: bool = Field(default=True)

    # -- LLM providers --------------------------------------------------------
    # PRIMARY: OpenAI (ChatGPT) — set OPENAI_API_KEY in .env
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")

    # FALLBACK: Ollama (local, free)
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3.1:8b", alias="OLLAMA_MODEL")

    # Legacy Gemini config (kept for backward compat but no longer primary)
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.0-flash", alias="GEMINI_MODEL")

    # Shared LLM settings
    llm_temperature: float = Field(default=0.1, alias="LLM_TEMPERATURE")
    llm_timeout_seconds: float = Field(default=45.0, alias="LLM_TIMEOUT_SECONDS")
    use_ollama_only: bool = Field(default=False, alias="USE_OLLAMA_ONLY")
    llm_max_retries: int = Field(default=2, ge=0, description="Retries per provider before failing over")

    # -- Pinecone vector memory (task #3) ------------------------------------
    pinecone_api_key: str = Field(default="", alias="PINECONE_API_KEY")
    pinecone_index_name: str = Field(default="claimblitz-memory", alias="PINECONE_INDEX_NAME")
    pinecone_cloud: str = Field(default="aws", alias="PINECONE_CLOUD")
    pinecone_region: str = Field(default="us-east-1", alias="PINECONE_REGION")
    # Pinecone Local (docker emulator) support for dev/test without a real key.
    # https://docs.pinecone.io -- run via `ghcr.io/pinecone-io/pinecone-local`.
    # Verified working against a live container during task #3 (see
    # agentcore/pinecone_memory.py for the http:// TLS-disable workaround
    # Pinecone Local requires).
    pinecone_use_local: bool = Field(default=False, alias="PINECONE_USE_LOCAL")
    pinecone_local_host: str = Field(default="http://localhost:5081", alias="PINECONE_LOCAL_HOST")
    # Embeddings: OpenAI's text-embedding-3-small (1536 dims, fast+cheap)
    embedding_model: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL")
    embedding_dimension: int = Field(default=1536, alias="EMBEDDING_DIMENSION")

    # -- MongoDB (replacing Postgres) ------------------------------------------
    mongodb_url: str = Field(default="mongodb://localhost:27017", alias="MONGODB_URL")
    mongodb_db_name: str = Field(default="claimblitz", alias="MONGODB_DB_NAME")

    # -- Postgres (legacy, kept for reference but no longer used) -------------
    postgres_dsn: str = Field(
        default="postgresql+asyncpg://claimblitz:claimblitz@localhost:5432/claimblitz",
        alias="POSTGRES_DSN",
    )

    # -- Redis working memory / blackboard (task #7) -------------------------
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    # -- RabbitMQ event bus (task #7/#9) -------------------------------------
    rabbitmq_url: str = Field(default="amqp://guest:guest@localhost:5672/", alias="RABBITMQ_URL")

    # -- Security (task #12) --------------------------------------------------
    jwt_secret_key: str = Field(default="", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(default=30, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    rate_limit_per_minute: int = Field(default=60, alias="RATE_LIMIT_PER_MINUTE")

    # -- Observability (task #11) ---------------------------------------------
    otel_exporter_otlp_endpoint: str = Field(default="", alias="OTEL_EXPORTER_OTLP_ENDPOINT")
    sentry_dsn: str = Field(default="", alias="SENTRY_DSN")
    prometheus_enabled: bool = Field(default=True, alias="PROMETHEUS_ENABLED")

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache(maxsize=1)
def get_settings() -> AgentCoreSettings:
    """Cached accessor, mirroring the existing ``get_llm_client()`` pattern."""
    return AgentCoreSettings()


__all__ = ["AgentCoreSettings", "get_settings"]
