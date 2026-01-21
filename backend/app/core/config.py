"""
Application configuration using Pydantic Settings.

This module manages all environment variables and application settings.
It provides type-safe configuration with automatic validation.
"""

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
        default=None, description="LangSmith API key", repr=False)
    langsmith_project: str = Field(
        default="integration-forge",
        description="LangSmith project name"
    )
    langsmith_tracing: bool = Field(
        default=True, description="Enable LangSmith tracing")

    # Cohere Configuration (for re-ranking)
    cohere_api_key: str | None = Field(
        default=None, description="Cohere API key", repr=False)
    cohere_model: str = Field(
        default="rerank-english-v3.0", description="Cohere rerank model")

    # RAG Configuration
    chunk_size: int = Field(
        default=1000, description="Default chunk size for text splitting")
    chunk_overlap: int = Field(
        default=200, description="Chunk overlap for context continuity")
    top_k: int = Field(default=10, description="Number of chunks to retrieve")
    rerank_top_k: int = Field(
        default=5, description="Number of chunks after re-ranking")

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


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache to ensure settings are loaded only once.

    Returns:
        Settings: Application settings instance
    """
    return Settings()


# Export settings instance for easy import
settings = get_settings()
