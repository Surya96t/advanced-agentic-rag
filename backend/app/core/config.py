"""
Application configuration using Pydantic Settings.

This module manages all environment variables and application settings.
It provides type-safe configuration with automatic validation.
"""

import os
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings are loaded from .env file or environment variables.
    Required fields will raise an error if not set.
    """

    # Application Settings
    app_name: str = "Integration Forge"
    app_version: str = "0.1.0"
    environment: Literal["development",
                         "staging", "production"] = "development"
    debug: bool = Field(default=True, description="Enable debug mode")

    # Server Settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    reload: bool = Field(
        default=True, description="Auto-reload on code changes")

    # CORS Settings
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001"],
        description="Allowed CORS origins"
    )
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]

    # Supabase Configuration
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_service_key: str = Field(
        ...,
        description="Supabase service role key (for backend operations)",
        repr=False,
        alias="SUPABASE_SERVICE_ROLE_KEY"  # Use service role key for admin operations
    )

    # Database Settings
    db_pool_size: int = Field(
        default=10, description="Database connection pool size")
    db_max_overflow: int = Field(
        default=20, description="Max overflow connections")
    db_timeout: int = Field(
        default=30, description="Database timeout in seconds")

    # OpenAI Configuration
    openai_api_key: str = Field(..., description="OpenAI API key", repr=False)
    openai_model: str = Field(
        default="gpt-4o", description="OpenAI model for chat")
    openai_embedding_model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI model for embeddings (1536 dimensions)"
    )
    openai_embedding_dimensions: int = Field(
        default=1536,
        description="Embedding vector dimensions (text-embedding-3-small)"
    )
    openai_max_tokens: int = Field(
        default=4096, description="Max tokens for responses")
    openai_temperature: float = Field(
        default=0.7, description="Temperature for responses")

    # LangSmith Configuration (Optional - for observability)
    langsmith_api_key: str | None = Field(
        default=None,
        description="LangSmith API key",
        repr=False,
        alias="LANGCHAIN_API_KEY"
    )
    langsmith_project: str = Field(
        default="integration-forge-rag",
        description="LangSmith project name",
        alias="LANGCHAIN_PROJECT"
    )
    langsmith_tracing: bool = Field(
        default=True,
        description="Enable LangSmith tracing",
        alias="LANGCHAIN_TRACING_V2"
    )

    # Cohere Configuration (for re-ranking)
    cohere_api_key: str | None = Field(
        default=None, description="Cohere API key", repr=False)
    cohere_model: str = Field(
        default="rerank-english-v3.0", description="Cohere rerank model")

    # RAG Configuration - Chunking
    chunk_size: int = Field(
        default=1000, description="Default chunk size for text splitting")
    chunk_overlap: int = Field(
        default=200, description="Chunk overlap for context continuity")

    # RAG Configuration - Vector Search
    vector_search_top_k: int = Field(
        default=20,
        description="Number of results from vector search (semantic)"
    )
    vector_search_min_similarity: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity threshold (0.0-1.0)"
    )

    # RAG Configuration - Text Search
    text_search_top_k: int = Field(
        default=20,
        description="Number of results from text search (keyword)"
    )
    text_search_min_rank: float = Field(
        default=0.01,
        ge=0.0,
        description="Minimum ts_rank score threshold for FTS"
    )

    # RAG Configuration - Hybrid Search
    hybrid_search_alpha: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Weight for vector vs text (0.0=text only, 1.0=vector only, 0.5=equal)"
    )
    hybrid_rrf_k: int = Field(
        default=60,
        description="Reciprocal Rank Fusion constant (controls score decay)"
    )

    # RAG Configuration - Re-ranking
    rerank_enabled: bool = Field(
        default=True,
        description="Enable re-ranking of search results"
    )
    rerank_model: str = Field(
        default="ms-marco-MiniLM-L-6-v2",
        description="FlashRank model name (TinyBERT, MiniLM-L-6, MiniLM-L-12)"
    )
    rerank_top_k: int = Field(
        default=10,
        description="Number of results to return after re-ranking"
    )

    # Legacy field for backwards compatibility
    top_k: int = Field(
        default=10,
        description="(Deprecated) Use rerank_top_k instead"
    )

    # Rate Limiting
    rate_limit_per_minute: int = Field(
        default=60, description="API rate limit per minute")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="json", description="Log format: json or console")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Parse CORS origins from comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment is one of the allowed values."""
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"environment must be one of {allowed}")
        return v

    @model_validator(mode="after")
    def enforce_production_safety(self) -> "Settings":
        """
        Enforce safe defaults for production environment.

        Raises:
            ValueError: If production environment has unsafe configuration
        """
        if self.environment == "production":
            if self.debug:
                raise ValueError(
                    "DEBUG mode must be disabled in production (set DEBUG=false)"
                )
            if self.reload:
                raise ValueError(
                    "Auto-reload must be disabled in production (set RELOAD=false)"
                )
            if self.host == "0.0.0.0":
                raise ValueError(
                    "Host must not be 0.0.0.0 in production (use 127.0.0.1 or specific IP)"
                )
        return self

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"

    @property
    def supabase_connection_string(self) -> str:
        """
        Build PostgreSQL connection string for Supabase.

        Used by LangGraph checkpointer for persistent state storage.

        Returns:
            PostgreSQL connection string in format:
            postgresql://postgres:[password]@[host]:5432/postgres
        """
        # Extract components from Supabase URL
        # Format: https://[project-ref].supabase.co
        # PostgreSQL: [project-ref].pooler.supabase.com:5432

        project_ref = self.supabase_url.replace(
            "https://", "").replace(".supabase.co", "")

        # Use service role key as password (base64 encoded JWT)
        # Note: For direct PostgreSQL access, you may need database password
        # This is a simplified version - update with actual DB credentials if needed
        return f"postgresql://postgres.{project_ref}:5432/postgres"


# Set up LangSmith environment variables (auto-configured)


def configure_langsmith(settings: Settings) -> None:
    """
    Configure LangSmith environment variables for observability.

    This function is called automatically when settings are loaded.
    """
    if settings.langsmith_tracing:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"

        if settings.langsmith_api_key:
            os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key

        os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache to ensure settings are loaded only once.
    Also configures LangSmith environment variables.

    Returns:
        Settings: Application settings instance
    """
    settings_instance = Settings()
    configure_langsmith(settings_instance)
    return settings_instance


# Export settings instance for easy import
settings = get_settings()
