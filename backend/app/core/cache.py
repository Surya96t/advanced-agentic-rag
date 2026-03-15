"""Redis-based response cache for the chat endpoint.

Caches non-streaming chat responses keyed by user_id + SHA-256(normalised query).
All operations fail open — if Redis is unavailable the caller proceeds normally.

Key format:  cache:query:{user_id}:{sha256(lower(stripped(query)))}
TTL default: 24 hours (configurable via CACHE_TTL_SECONDS)

Invalidation: call invalidate_user(user_id) after a successful document ingest so
              stale answers are never served after the knowledge base changes.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

import ssl as _ssl

from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import RedisError

from app.core.config import settings

logger = logging.getLogger(__name__)

# Module-level pool — created once and reused across requests.
_pool: ConnectionPool | None = None
_redis: Redis | None = None


def _get_redis() -> Redis:
    """Return a shared async Redis client, creating it on first call."""
    global _pool, _redis
    if _redis is None:
        url = settings.redis_url
        ssl_kwargs: dict = {}
        if url.startswith("rediss://"):
            ssl_kwargs["ssl_cert_reqs"] = _ssl.CERT_NONE
        _pool = ConnectionPool.from_url(
            url,
            max_connections=settings.redis_connection_pool_size,
            decode_responses=True,
            socket_timeout=2.0,
            socket_connect_timeout=2.0,
            **ssl_kwargs,
        )
        _redis = Redis(connection_pool=_pool)
        logger.info("Redis cache client initialised")
    return _redis


def _cache_key(user_id: str, query: str) -> str:
    """Build a user-scoped cache key from the normalised query."""
    normalised = query.strip().lower()
    digest = hashlib.sha256(normalised.encode()).hexdigest()
    return f"cache:query:{user_id}:{digest}"


async def get_cached_response(user_id: str, query: str) -> dict[str, Any] | None:
    """
    Return the cached response dict for *query* by *user_id*, or None on miss/error.

    Args:
        user_id: The authenticated user's ID (used to scope the cache key).
        query:   The user's raw query string.

    Returns:
        Deserialised response dict on a cache hit, None otherwise.
    """
    if not settings.cache_enabled:
        return None
    try:
        client = _get_redis()
        key = _cache_key(user_id, query)
        raw = await client.get(key)
        if raw is None:
            logger.debug("Cache miss", extra={"user_id": user_id, "key": key})
            return None
        logger.info("Cache hit", extra={"user_id": user_id, "key": key})
        return json.loads(raw)
    except RedisError as exc:
        logger.warning(
            "Redis unavailable — cache get skipped",
            extra={"user_id": user_id, "error": str(exc)},
        )
        return None
    except Exception as exc:
        logger.warning(
            "Cache get failed unexpectedly",
            extra={"user_id": user_id, "error": str(exc)},
        )
        return None


async def cache_response(
    user_id: str,
    query: str,
    response: dict[str, Any],
    ttl: int | None = None,
) -> None:
    """
    Store *response* in the cache under the key for (*user_id*, *query*).

    Args:
        user_id:  The authenticated user's ID.
        query:    The user's raw query string.
        response: Serialisable response dict to cache.
        ttl:      TTL in seconds; defaults to ``settings.cache_ttl_seconds``.
    """
    if not settings.cache_enabled:
        return
    ttl = ttl if ttl is not None else settings.cache_ttl_seconds
    try:
        client = _get_redis()
        key = _cache_key(user_id, query)
        await client.setex(key, ttl, json.dumps(response))
        logger.debug(
            "Response cached",
            extra={"user_id": user_id, "key": key, "ttl": ttl},
        )
    except RedisError as exc:
        logger.warning(
            "Redis unavailable — cache set skipped",
            extra={"user_id": user_id, "error": str(exc)},
        )
    except Exception as exc:
        logger.warning(
            "Cache set failed unexpectedly",
            extra={"user_id": user_id, "error": str(exc)},
        )


async def invalidate_user(user_id: str) -> int:
    """
    Delete all cached responses for *user_id*.

    Called after a successful document ingest so stale answers are evicted.

    Args:
        user_id: The authenticated user's ID.

    Returns:
        Number of keys deleted (0 on error or empty cache).
    """
    if not settings.cache_enabled:
        return 0
    try:
        client = _get_redis()
        pattern = f"cache:query:{user_id}:*"
        # SCAN instead of KEYS to avoid blocking the Redis event loop on large keyspaces.
        deleted = 0
        async for key in client.scan_iter(match=pattern, count=100):
            await client.delete(key)
            deleted += 1
        if deleted:
            logger.info(
                "User cache invalidated",
                extra={"user_id": user_id, "keys_deleted": deleted},
            )
        return deleted
    except RedisError as exc:
        logger.warning(
            "Redis unavailable — cache invalidation skipped",
            extra={"user_id": user_id, "error": str(exc)},
        )
        return 0
    except Exception as exc:
        logger.warning(
            "Cache invalidation failed unexpectedly",
            extra={"user_id": user_id, "error": str(exc)},
        )
        return 0
