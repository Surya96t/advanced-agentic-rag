"""
Application configuration using Pydantic Settings.

This module manages all environment variables and application settings.
It provides type-safe configuration with automatic validation.
"""

import logging
import os
from functools import lru_cache
from typing import Literal
from urllib.parse import quote_plus, urlparse

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings are loaded from .env file or environment variables.
    Required fields will raise an error if not set.
    """

    # Application Settings
    app_name: str = "RAG Assistant"
    app_version: str = "0.1.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = Field(default=False, description="Enable debug mode (always False in production)")

    # Server Settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    reload: bool = Field(default=True, description="Auto-reload on code changes")

    # CORS Settings
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001"],
        description="Allowed CORS origins",
    )
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["GET", "POST", "PATCH", "DELETE", "OPTIONS"]
    cors_allow_headers: list[str] = ["Content-Type", "Authorization", "X-Revalidate-Secret"]

    # Supabase Configuration
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_service_key: str = Field(
        ...,
        description="Supabase service role key (for backend operations)",
        repr=False,
        alias="SUPABASE_SERVICE_ROLE_KEY",  # Use service role key for admin operations
    )
    supabase_db_password: str = Field(
        ...,
        description="Supabase database password (for direct PostgreSQL connection)",
        repr=False,
        alias="SUPABASE_DB_PASSWORD",
    )
    supabase_pooler_region: str = Field(
        default="aws-1-us-east-1",
        description="Supabase pooler region (e.g., aws-1-us-east-1, aws-0-us-west-1)",
    )

    # Database Settings
    db_pool_size: int = Field(default=10, description="Database connection pool size")
    db_max_overflow: int = Field(default=20, description="Max overflow connections")
    db_timeout: int = Field(default=30, description="Database timeout in seconds")

    # OpenAI Configuration
    openai_api_key: str = Field(..., description="OpenAI API key", repr=False)
    openai_model: str = Field(default="gpt-4o-mini", description="OpenAI model for chat")
    openai_embedding_model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI model for embeddings (1536 dimensions)",
    )
    openai_embedding_dimensions: int = Field(
        default=1536, description="Embedding vector dimensions (text-embedding-3-small)"
    )
    openai_max_tokens: int = Field(default=4096, description="Max tokens for responses")
    openai_temperature: float = Field(default=0.7, description="Temperature for responses")

    # LangSmith Configuration (Optional - for observability)
    langsmith_api_key: str | None = Field(
        default=None, description="LangSmith API key", repr=False, alias="LANGCHAIN_API_KEY"
    )
    langsmith_project: str = Field(
        default="integration-forge-rag",
        description="LangSmith project name",
        alias="LANGCHAIN_PROJECT",
    )
    langsmith_tracing: bool = Field(
        default=True, description="Enable LangSmith tracing", alias="LANGCHAIN_TRACING_V2"
    )

    # Cohere Configuration (for re-ranking)
    cohere_api_key: str | None = Field(default=None, description="Cohere API key", repr=False)
    cohere_model: str = Field(default="rerank-english-v3.0", description="Cohere rerank model")

    # Clerk Authentication Configuration
    clerk_secret_key: str = Field(
        ..., description="Clerk secret key for JWT validation", repr=False
    )
    clerk_publishable_key: str = Field(..., description="Clerk publishable key")
    clerk_issuer_url: str = Field(
        ..., description="Clerk issuer URL (e.g., https://your-app.clerk.accounts.dev)"
    )
    clerk_jwks_cache_ttl: int = Field(
        default=3600, description="JWKS cache TTL in seconds (default: 1 hour)"
    )
    auth_enabled: bool = Field(
        default=True, description="Enable JWT authentication (disable for testing)"
    )

    # Redis Configuration
    redis_url_override: str | None = Field(
        default=None,
        alias="REDIS_URL",
        description="Full Redis URL (e.g. from Upstash). If set, takes precedence over individual host/port/password fields.",
        repr=False,
    )
    redis_host: str = Field(default="localhost", description="Redis server hostname")
    redis_port: int = Field(default=6379, ge=1, le=65535, description="Redis server port")
    redis_db: int = Field(default=0, ge=0, le=15, description="Redis database number (0-15)")
    redis_password: str | None = Field(
        default=None, description="Redis password (optional)", repr=False
    )
    redis_ssl: bool = Field(default=False, description="Use SSL/TLS for Redis connection")
    redis_ssl_cert_reqs: str | None = Field(
        default=None,
        alias="REDIS_SSL_CERT_REQS",
        description="SSL certificate verification mode for Redis TLS connections. "
        "Accepted values: CERT_REQUIRED (default), CERT_OPTIONAL, CERT_NONE. "
        "Only needed when using a rediss:// URL with a self-signed certificate.",
    )
    redis_connection_pool_size: int = Field(
        default=10, ge=1, le=100, description="Redis connection pool size"
    )

    # Response Cache Configuration
    cache_enabled: bool = Field(
        default=True, description="Enable Redis response caching for non-streaming chat"
    )
    cache_ttl_seconds: int = Field(
        default=86400, ge=60, description="Cache TTL in seconds (default: 24 hours)"
    )

    # Rate Limiting Configuration
    rate_limit_enabled: bool = Field(
        default=True, description="Enable rate limiting (disable for load testing)"
    )
    rate_limit_default_requests: int = Field(
        default=50, ge=1, description="Default requests per hour"
    )
    rate_limit_default_window: int = Field(
        default=3600, ge=60, description="Rate limit window in seconds"
    )
    rate_limit_burst_multiplier: float = Field(
        default=1.5, ge=1.0, le=3.0, description="Burst allowance multiplier"
    )

    # Per-Endpoint Rate Limits (requests per hour)
    rate_limit_ingest: int = Field(
        default=10, ge=1, description="Ingestion endpoint rate limit (expensive: OpenAI embeddings)"
    )
    rate_limit_chat: int = Field(default=50, ge=1, description="Chat endpoint rate limit")
    rate_limit_documents: int = Field(default=200, ge=1, description="Document listing rate limit")

    # RAG Configuration - Chunking
    chunk_size: int = Field(default=1000, description="Default chunk size for text splitting")
    chunk_overlap: int = Field(default=200, description="Chunk overlap for context continuity")

    # RAG Configuration - Vector Search
    vector_search_top_k: int = Field(
        default=20, description="Number of results from vector search (semantic)"
    )
    vector_search_min_similarity: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Minimum cosine similarity threshold (0.0-1.0)"
    )

    # RAG Configuration - Text Search
    text_search_top_k: int = Field(
        default=20, description="Number of results from text search (keyword)"
    )
    text_search_min_rank: float = Field(
        default=0.01, ge=0.0, description="Minimum ts_rank score threshold for FTS"
    )

    # RAG Configuration - Hybrid Search
    hybrid_search_alpha: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Weight for vector vs text (0.0=text only, 1.0=vector only, 0.7=favour semantic)",
    )
    hybrid_rrf_k: int = Field(
        default=60, description="Reciprocal Rank Fusion constant (controls score decay)"
    )

    # RAG Configuration - Re-ranking
    rerank_enabled: bool = Field(default=True, description="Enable re-ranking of search results")
    rerank_model: str = Field(
        default="ms-marco-MiniLM-L-6-v2",
        description="FlashRank model name (TinyBERT, MiniLM-L-6, MiniLM-L-12)",
    )
    rerank_top_k: int = Field(default=5, description="Number of results to return after re-ranking")

    # RAG Configuration - Validation
    validation_pass_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum quality score for a response to pass validation (0.0-1.0)",
    )
    validation_retry_threshold: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Quality score below which a response is immediately retried (0.0-1.0)",
    )
    validation_max_retries: int = Field(
        default=2, ge=0, description="Maximum number of validation-triggered retries"
    )

    # Legacy field for backwards compatibility
    top_k: int = Field(default=10, description="(Deprecated) Use rerank_top_k instead")

    # Legacy rate limiting field for backwards compatibility
    rate_limit_per_minute: int = Field(
        default=60,
        description="(Deprecated) Use rate_limit_default_requests and rate_limit_default_window instead",
    )

    # LangGraph Checkpointing Configuration
    enable_checkpointing: bool = Field(
        default=True,
        description="Enable LangGraph PostgreSQL checkpointing for conversation and agent state persistence",
    )

    # Conversational Memory Configuration
    max_conversation_tokens: int = Field(
        default=8000,
        ge=1000,
        le=100000,
        description="Max tokens for conversation history (reserve space for system prompt + retrieval context)",
    )
    recent_message_count: int = Field(
        default=10,
        ge=2,
        le=50,
        description="Number of recent messages to always keep (sliding window)",
    )

    # Storage Configuration
    storage_backend: Literal["supabase", "azure"] = Field(
        default="supabase",
        description="File storage backend: 'supabase' or 'azure'",
        alias="STORAGE_BACKEND",
    )
    storage_bucket: str = Field(
        default="documents",
        description="Storage bucket / container name for uploaded documents",
        alias="STORAGE_BUCKET",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format: json or console")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
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
                raise ValueError("DEBUG mode must be disabled in production (set DEBUG=false)")
            if self.reload:
                raise ValueError("Auto-reload must be disabled in production (set RELOAD=false)")
        return self

    @model_validator(mode="after")
    def validate_langsmith_config(self) -> "Settings":
        """
        Validate LangSmith configuration and disable tracing if API key is missing.

        This prevents errors when LangSmith tracing is enabled but no API key is provided.
        Automatically disables tracing in this case and logs a warning.

        Returns:
            Settings: Self with corrected langsmith_tracing value
        """
        if self.langsmith_tracing and not self.langsmith_api_key:
            # Disable tracing if API key is missing
            # Use object.__setattr__ because Settings is frozen after validation
            object.__setattr__(self, "langsmith_tracing", False)
            # Note: We can't log here because logger isn't initialized yet
            # The warning will be logged when configure_langsmith() is called
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
    def redis_url(self) -> str:
        """
        Build Redis connection URL.

        If REDIS_URL env var is set (e.g. from Upstash), use it directly.
        Otherwise, build from individual host/port/password/ssl fields.

        When REDIS_SSL_CERT_REQS is set, appends it as a URL query parameter
        so redis-py parses it correctly regardless of client type (sync/async/Celery).
        This is more reliable than passing ssl_cert_reqs as a Python kwarg to
        ConnectionPool.from_url.
        """
        if self.redis_url_override:
            base = self.redis_url_override
        else:
            protocol = "rediss" if self.redis_ssl else "redis"
            # URL-encode password to handle special characters safely
            if self.redis_password:
                encoded_password = quote_plus(self.redis_password)
                auth = f":{encoded_password}@"
            else:
                auth = ""
            base = f"{protocol}://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

        # Append ssl_cert_reqs as a URL query param when set — this is the
        # approach redis-py reliably handles for all client types.
        # redis-py URL parser only accepts lowercase: none/optional/required.
        # Normalise here so both redis-py (rate limiter/cache/backend) and
        # kombu (Celery broker) receive a value they can parse.
        if self.redis_ssl_cert_reqs and "ssl_cert_reqs" not in base:
            normalised = self.redis_ssl_cert_reqs.lower().removeprefix("cert_")
            sep = "&" if "?" in base else "?"
            base = f"{base}{sep}ssl_cert_reqs={normalised}"

        return base

    @property
    def supabase_connection_string(self) -> str:
        """
        Build PostgreSQL connection string for Supabase.

        Used by LangGraph checkpointer for persistent state storage.
        Uses direct database connection (no pooler) for development reliability.

        Returns:
            PostgreSQL connection string in format:
            postgresql://postgres.[project-ref]:[password]@[region].pooler.supabase.com:5432/postgres

        Example:
            >>> settings.supabase_url = "https://abc123.supabase.co"
            >>> settings.supabase_connection_string
            'postgresql://postgres.abc123:****@aws-0-us-west-1.pooler.supabase.com:5432/postgres'
        """
        # Parse Supabase URL to extract project reference
        # Format: https://[project-ref].supabase.co
        parsed = urlparse(self.supabase_url)
        hostname = parsed.netloc or parsed.path.rstrip("/")

        # Extract project reference by removing .supabase.co suffix
        if hostname.endswith(".supabase.co"):
            project_ref = hostname[: -len(".supabase.co")]
        else:
            # Fallback: use hostname as-is (for custom domains or local dev)
            project_ref = hostname.rstrip("/").lower()

        # Build PostgreSQL connection string using Transaction Pooler
        # Transaction pooler is ideal for serverless/short-lived connections
        #
        # Connection details:
        # - User: postgres.{project-ref} (qualified username)
        # - Host: aws-1-us-east-1.pooler.supabase.com (regional transaction pooler)
        # - Port: 6543 (transaction pooler port, NOT 5432)
        # - Database: postgres (default database)
        #
        # CRITICAL: Use SESSION POOLER (port 5432) instead of Transaction Pooler (port 6543)
        # Transaction pooler does NOT support prepared statements, causing "prepared statement already exists" errors
        # Session pooler maintains connection state and supports prepared statements
        username = f"postgres.{project_ref}"
        # Session pooler endpoint (supports prepared statements)
        # Region is configurable via SUPABASE_POOLER_REGION env var
        host = f"{self.supabase_pooler_region}.pooler.supabase.com"
        password = self.supabase_db_password
        database = "postgres"
        port = 5432  # SESSION POOLER port (was 6543 for transaction pooler)

        # URL-encode password in case it contains special characters
        encoded_password = quote_plus(password)

        return f"postgresql://{username}:{encoded_password}@{host}:{port}/{database}"


# Set up LangSmith environment variables (auto-configured)


def configure_langsmith(settings: Settings) -> None:
    """
    Configure LangSmith environment variables for observability.

    This function is called automatically when settings are loaded.
    Logs a warning if tracing was requested but disabled due to missing API key.
    """
    # Capture original environment value before modifying
    original_tracing = os.getenv("LANGCHAIN_TRACING_V2", "")

    if settings.langsmith_tracing:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"

        if settings.langsmith_api_key:
            os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
        else:
            # This should not happen due to validator, but handle defensively
            _logger.warning("LangSmith tracing enabled but API key is missing")

        os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
    else:
        # Tracing is disabled (possibly auto-disabled by validator)
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        # Check if it was auto-disabled (user requested but validator disabled it)
        if original_tracing.lower() == "true" and not settings.langsmith_api_key:
            _logger.info("LangSmith tracing disabled (API key not provided)")


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
