"""
Database connection pooling management.

Provides a shared AsyncConnectionPool for raw SQL operations, optimized for
concurrent access to the database (bypassing the Supabase HTTP API).
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from psycopg_pool import AsyncConnectionPool

from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DatabasePool:
    _pool: AsyncConnectionPool | None = None

    @classmethod
    async def open(cls):
        """Initialize the connection pool."""
        if cls._pool is None:
            logger.info("Initializing database connection pool")
            try:
                cls._pool = AsyncConnectionPool(
                    conninfo=settings.supabase_connection_string,
                    open=False,  # We'll open explicitly
                    min_size=1,
                    max_size=10,
                    timeout=30.0,
                )
                await cls._pool.open()
                logger.info("Database connection pool initialized")
            except Exception as e:
                logger.error(f"Failed to initialize database pool: {e}")
                raise

    @classmethod
    async def close(cls):
        """Close the connection pool."""
        if cls._pool:
            logger.info("Closing database connection pool")
            await cls._pool.close()
            cls._pool = None

    @classmethod
    @asynccontextmanager
    async def get_connection(cls) -> AsyncGenerator:
        """Get a connection from the pool."""
        if cls._pool is None:
            # Fallback initialization for dev/scripts (not ideal for prod)
            await cls.open()

        async with cls._pool.connection() as conn:
            yield conn


# Global instance accessor
async def get_db_pool() -> AsyncConnectionPool:
    if DatabasePool._pool is None:
        await DatabasePool.open()
    return DatabasePool._pool
