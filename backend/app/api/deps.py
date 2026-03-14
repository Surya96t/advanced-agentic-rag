"""
Shared dependencies for API routes.

This module provides dependency injection functions for FastAPI endpoints,
including JWT authentication and Redis-based rate limiting.
"""

import time
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.core.auth import get_current_user
from app.core.rate_limiter import get_rate_limiter
from app.database.client import SupabaseClient, get_db
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def get_current_user_id(user_id: Annotated[str, Depends(get_current_user)]) -> str:
    """
    Get current authenticated user ID from JWT token.

    This dependency:
    - Extracts JWT from Authorization header
    - Validates token signature and claims with Clerk JWKS
    - Returns user ID from 'sub' claim
    - Respects AUTH_ENABLED toggle (returns 'dev-user' if disabled)

    Returns:
        User ID string from JWT 'sub' claim (Clerk format: "user_2bXYZ123")

    Raises:
        HTTPException: 401 Unauthorized if token is invalid/missing

    Example:
        ```python
        @router.get("/documents")
        def list_documents(user_id: UserID):
            # user_id will be extracted from JWT token
            documents = document_repo.list_by_user(user_id)
            return documents
        ```
    """
    return user_id


async def check_user_rate_limit(
    request: Request,
    user_id: Annotated[str, Depends(get_current_user_id)]
) -> tuple[int, int, int]:
    """
    Check if current user has exceeded rate limit using Redis sliding window.

    Uses Redis-based rate limiter with:
    - Per-endpoint limits (chat: 100/hr, ingest: 20/hr, etc.)
    - Sliding window algorithm for accurate rate limiting
    - Graceful degradation if Redis fails

    Args:
        user_id: Current user's ID (injected via dependency)

    Returns:
        Tuple of (limit, remaining, reset_time) for adding to response headers

    Raises:
        HTTPException: 429 Too Many Requests if limit exceeded

    Example:
        ```python
        @router.post("/chat")
        def chat(
            request: ChatRequest,
            rate_limit_info: RateLimitInfo,
            user_id: UserID
        ):
            # Rate limit checked automatically before endpoint executes
            # rate_limit_info contains (limit, remaining, reset) for headers
            return chat_service.process(request, user_id)
        ```
    """
    # Get rate limiter instance
    limiter = get_rate_limiter()

    # Extract endpoint name from the path: /api/v1/<endpoint>/...  → <endpoint>
    path_parts = request.url.path.strip("/").split("/")
    endpoint = path_parts[2] if len(path_parts) > 2 else "default"

    allowed, limit, remaining = limiter.check_rate_limit(
        user_id, endpoint=endpoint)

    # Debug: Log the rate limit check result
    logger.debug(
        "Rate limit check: user_id=%s, allowed=%s, limit=%d, remaining=%d",
        user_id, allowed, limit, remaining
    )

    # Calculate reset time (window end)
    reset_time = int(time.time()) + 3600  # 1 hour from now

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
            headers={
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_time),
                "Retry-After": "3600",
            }
        )
    
    # Return rate limit info for successful requests
    # If rate limiting is disabled (limit=0), return (0, 0, 0) to signal frontend to skip
    return (limit, remaining, reset_time)


# ============================================================================
# Type Aliases for Dependency Injection
# ============================================================================
# These aliases make endpoint signatures cleaner and more readable.
# Instead of:    user_id: Annotated[str, Depends(get_current_user_id)]
# You can write:  user_id: UserID

UserID = Annotated[str, Depends(get_current_user_id)]
"""Type alias for user ID dependency injection."""

RateLimitInfo = Annotated[tuple[int, int, int], Depends(check_user_rate_limit)]
"""Type alias for rate limit info (limit, remaining, reset) dependency injection."""

DatabaseClient = Annotated[SupabaseClient, Depends(get_db)]
"""Type alias for Supabase client dependency injection."""
