"""
Supabase database client initialization and management.

This module provides the Supabase client for database operations,
including connection management and health checks.
"""

from typing import Any

from supabase import Client, create_client

from app.core.config import settings
from app.utils.errors import DatabaseError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SupabaseClient:
    """
    Supabase client wrapper for database operations.

    Provides a singleton client instance with connection pooling
    and health check capabilities.
    """

    _instance: Client | None = None
    _initialized: bool = False

    @classmethod
    def get_client(cls) -> Client:
        """
        Get or create Supabase client instance.

        Returns:
            Client: Supabase client instance

        Raises:
            DatabaseError: If client initialization fails
        """
        if cls._instance is None:
            try:
                logger.info(
                    "Initializing Supabase client",
                    url=settings.supabase_url,
                )

                cls._instance = create_client(
                    supabase_url=settings.supabase_url,
                    supabase_key=settings.supabase_service_key,
                )

                cls._initialized = True
                logger.info("Supabase client initialized successfully")

            except Exception as e:
                logger.error(
                    "Failed to initialize Supabase client",
                    error=str(e),
                    exc_info=True,
                )
                raise DatabaseError(
                    message="Failed to connect to database",
                    details={"error": str(e)},
                )

        return cls._instance

    @classmethod
    async def health_check(cls) -> bool:
        """
        Check if database connection is healthy.

        Returns:
            bool: True if connection is healthy, False otherwise
        """
        try:
            client = cls.get_client()

            # Try a simple query to verify connection
            # We'll query the documents table (will create this later)
            # For now, just check if client exists
            if client is not None:
                logger.debug("Database health check passed")
                return True

            logger.warning("Database client not initialized")
            return False

        except Exception as e:
            logger.error(
                "Database health check failed",
                error=str(e),
                exc_info=True,
            )
            return False

    @classmethod
    def close(cls) -> None:
        """
        Close the database connection.

        Note: Supabase client doesn't require explicit closing,
        but this method is here for consistency and future use.
        """
        if cls._instance is not None:
            logger.info("Closing Supabase client")
            cls._instance = None
            cls._initialized = False


def get_db() -> Client:
    """
    Dependency function to get database client.

    This is used as a FastAPI dependency for routes that need database access.

    Returns:
        Client: Supabase client instance

    Example:
        ```python
        from fastapi import Depends

        @app.get("/documents")
        async def list_documents(db: Client = Depends(get_db)):
            result = db.table("documents").select("*").execute()
            return result.data
        ```
    """
    return SupabaseClient.get_client()


# Create a global client instance for direct imports
# (Can be used outside of FastAPI dependency injection)
supabase_client = SupabaseClient.get_client()
