"""Redis-based rate limiting with sliding window algorithm."""

import logging
import time
from typing import Optional, Tuple
from uuid import uuid4

from redis import ConnectionPool, Redis
from redis.exceptions import RedisError

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisRateLimiter:
    """
    Redis-based rate limiter using sliding window algorithm.

    Uses Redis sorted sets (ZSET) to track request timestamps:
    - Score = timestamp (for range queries)
    - Member = unique request ID (timestamp + random)
    - Automatically removes old entries outside the window
    """

    def __init__(self):
        """Initialize Redis connection pool."""
        self._pool: Optional[ConnectionPool] = None
        self._redis: Optional[Redis] = None

    def _get_redis(self) -> Redis:
        """Get or create Redis client with connection pooling."""
        if self._redis is None:
            self._pool = ConnectionPool.from_url(
                settings.redis_url,
                max_connections=settings.redis_connection_pool_size,
                decode_responses=True,
            )
            self._redis = Redis(connection_pool=self._pool)
            logger.info("Redis rate limiter initialized")
        return self._redis

    def check_rate_limit(
        self, user_id: str, endpoint: str = "default"
    ) -> Tuple[bool, int, int]:
        """
        Check if user has exceeded rate limit for endpoint.

        Uses sliding window algorithm with check-first approach:
        1. PIPELINE 1 (check): Remove old entries + count current requests
        2. PIPELINE 2 (record): Only if allowed, record new request with unique ID

        This ensures:
        - Denied requests are never recorded in Redis
        - Each request has a unique ZSET member (timestamp + UUID)
        - No race conditions or ZSET collisions

        Args:
            user_id: User identifier
            endpoint: API endpoint name (for per-endpoint limits)

        Returns:
            Tuple of (allowed, limit, remaining):
            - allowed: True if request is allowed, False if rate limited
            - limit: Total requests allowed in window
            - remaining: Requests remaining in current window

        Raises:
            No exceptions - degrades gracefully if Redis fails
        """
        # If rate limiting is disabled, allow all requests
        if not settings.rate_limit_enabled:
            logger.info(
                f"[Rate Limiter] Rate limiting is DISABLED (settings.rate_limit_enabled=False) for user {user_id}"
            )
            return (True, 0, 0)

        try:
            redis_client = self._get_redis()
            key = get_rate_limit_key(user_id, endpoint)
            limit, window = get_endpoint_limits(endpoint)

            # Current timestamp
            now = time.time()
            window_start = now - window

            # PIPELINE 1: Check current request count (no recording yet)
            check_pipe = redis_client.pipeline()
            check_pipe.zremrangebyscore(
                key, 0, window_start)  # Remove old entries
            check_pipe.zcard(key)  # Count current entries
            check_pipe.expire(key, window)  # Set expiry for cleanup

            check_results = check_pipe.execute()
            current_count = check_results[1]  # ZCARD result

            # Determine if request is allowed
            allowed = current_count < limit

            if allowed:
                # PIPELINE 2: Record the request only if allowed
                # Use truly unique member: timestamp + UUID4
                unique_member = f"{now}-{uuid4()}"

                record_pipe = redis_client.pipeline()
                record_pipe.zadd(key, {unique_member: now})
                record_pipe.expire(key, window)  # Ensure expiry is set
                record_pipe.execute()

                # Remaining after recording this request
                remaining = max(0, limit - (current_count + 1))

                logger.debug(
                    f"Rate limit check passed for user {user_id} on {endpoint}: "
                    f"{current_count + 1}/{limit} requests"
                )
            else:
                # Request denied - don't record it at all
                remaining = 0

                logger.warning(
                    f"Rate limit exceeded for user {user_id} on {endpoint}: "
                    f"{current_count}/{limit} requests in {window}s window"
                )

            return (allowed, limit, remaining)

        except RedisError as e:
            # Graceful degradation: allow request if Redis fails
            logger.error(f"Redis error during rate limit check: {e}")
            logger.warning(
                "Rate limiter failing open - allowing request despite Redis error"
            )
            return (True, 0, 0)
        except Exception as e:
            # Unexpected errors also fail open
            logger.error(f"Unexpected error in rate limiter: {e}")
            return (True, 0, 0)

    def close(self):
        """Close Redis connection pool."""
        if self._pool:
            self._pool.disconnect()
            logger.info("Redis rate limiter connection pool closed")


# Singleton instance
_rate_limiter: Optional[RedisRateLimiter] = None


def get_rate_limiter() -> RedisRateLimiter:
    """
    Get singleton rate limiter instance.

    Returns:
        RedisRateLimiter: The global rate limiter instance.
    """
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RedisRateLimiter()
    return _rate_limiter


def get_rate_limit_key(user_id: str, endpoint: str) -> str:
    """
    Format Redis key for rate limiting.

    Args:
        user_id: User identifier
        endpoint: API endpoint name

    Returns:
        str: Redis key in format "ratelimit:{user_id}:{endpoint}"
    """
    return f"ratelimit:{user_id}:{endpoint}"


def get_endpoint_limits(endpoint: str) -> Tuple[int, int]:
    """
    Get rate limit configuration for endpoint.

    Args:
        endpoint: API endpoint name

    Returns:
        Tuple of (limit, window):
        - limit: Maximum requests allowed
        - window: Time window in seconds

    Example endpoint limits:
        - chat endpoints: 100 requests per hour
        - document upload: 20 requests per hour
        - document listing: 200 requests per hour
        - default: 100 requests per hour
    """
    # Map endpoint names to settings
    endpoint_map = {
        "ingest": settings.rate_limit_ingest,
        "chat": settings.rate_limit_chat,
        "documents": settings.rate_limit_documents,
    }

    # Get endpoint-specific limit or use default
    limit = endpoint_map.get(endpoint, settings.rate_limit_default_requests)
    window = settings.rate_limit_default_window

    return (limit, window)
