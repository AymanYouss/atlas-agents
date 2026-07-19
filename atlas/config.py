"""Central, typed configuration loaded from the environment.

Settings are read once and cached. Every module imports :func:`get_settings`
rather than reading ``os.environ`` directly, which keeps configuration in one
auditable place and makes it trivial to override in tests.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LLMProvider = Literal["anthropic", "openai"]


class Settings(BaseSettings):
    """Application settings, populated from environment variables / ``.env``."""

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Core ---
    env: Literal["development", "staging", "production", "test"] = Field(
        default="development", alias="ATLAS_ENV"
    )
    log_level: str = Field(default="INFO", alias="ATLAS_LOG_LEVEL")
    api_host: str = Field(default="0.0.0.0", alias="ATLAS_API_HOST")
    api_port: int = Field(default=8000, alias="ATLAS_API_PORT")
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        alias="ATLAS_CORS_ORIGINS",
    )

    # --- LLM ---
    llm_provider: LLMProvider = Field(default="anthropic", alias="ATLAS_LLM_PROVIDER")
    planner_model: str = Field(default="claude-opus-4-8", alias="ATLAS_PLANNER_MODEL")
    executor_model: str = Field(default="claude-sonnet-4-6", alias="ATLAS_EXECUTOR_MODEL")
    critic_model: str = Field(default="claude-opus-4-8", alias="ATLAS_CRITIC_MODEL")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")

    # --- Persistence ---
    database_url: str = Field(
        default="postgresql+asyncpg://atlas:atlas@localhost:5432/atlas",
        alias="ATLAS_DATABASE_URL",
    )

    # --- MCP / tools ---
    tavily_api_key: str | None = Field(default=None, alias="TAVILY_API_KEY")

    # --- Sandbox ---
    sandbox_image: str = Field(default="atlas-sandbox:latest", alias="ATLAS_SANDBOX_IMAGE")
    sandbox_cpu_limit: float = Field(default=1.0, alias="ATLAS_SANDBOX_CPU_LIMIT")
    sandbox_memory_limit: str = Field(default="512m", alias="ATLAS_SANDBOX_MEMORY_LIMIT")
    sandbox_timeout_seconds: int = Field(default=30, alias="ATLAS_SANDBOX_TIMEOUT_SECONDS")
    sandbox_network: str = Field(default="none", alias="ATLAS_SANDBOX_NETWORK")

    # --- Guardrails ---
    max_steps: int = Field(default=24, alias="ATLAS_MAX_STEPS")
    max_retries_per_step: int = Field(default=2, alias="ATLAS_MAX_RETRIES_PER_STEP")
    max_wall_clock_seconds: int = Field(default=900, alias="ATLAS_MAX_WALL_CLOCK_SECONDS")
    max_tokens_per_run: int = Field(default=2_000_000, alias="ATLAS_MAX_TOKENS_PER_RUN")

    # --- Observability ---
    enable_metrics: bool = Field(default=True, alias="ATLAS_ENABLE_METRICS")

    @field_validator("cors_origins")
    @classmethod
    def _strip_origins(cls, v: str) -> str:
        return ",".join(o.strip() for o in v.split(",") if o.strip())

    @property
    def cors_origin_list(self) -> list[str]:
        return [o for o in self.cors_origins.split(",") if o]

    @property
    def sync_database_url(self) -> str:
        """Sync driver URL used by the LangGraph Postgres checkpointer."""
        return self.database_url.replace("+asyncpg", "").replace(
            "postgresql://", "postgresql://"
        )

    @property
    def is_production(self) -> bool:
        return self.env == "production"


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()
