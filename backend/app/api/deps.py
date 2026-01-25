"""
Shared dependencies for API routes.

This module provides dependency injection functions for FastAPI endpoints,
including JWT authentication and Redis-based rate limiting.
"""

import time
from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.core.auth import get_current_user
from app.core.rate_limiter import get_rate_limiter
from app.database.client import SupabaseClient, get_db


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
    user_id: Annotated[str, Depends(get_current_user_id)]
) -> None:
    """
    Check if current user has exceeded rate limit using Redis sliding window.

    Uses Redis-based rate limiter with:
    - Per-endpoint limits (chat: 100/hr, ingest: 20/hr, etc.)
    - Sliding window algorithm for accurate rate limiting
    - Graceful degradation if Redis fails

    Args:
        user_id: Current user's ID (injected via dependency)

    Raises:
        HTTPException: 429 Too Many Requests if limit exceeded

    Example:
        ```python
        @router.post("/chat")
        def chat(
            request: ChatRequest,
            _: RateLimitCheck,  # Underscore = we don't use the return value
            user_id: UserID
        ):
            # Rate limit checked automatically before endpoint executes
            return chat_service.process(request, user_id)
        ```
    """
    # Get rate limiter instance
    limiter = get_rate_limiter()

    # Check rate limit (endpoint will be "default" - routes can override this)
    # TODO: Extract actual endpoint name from request context
    allowed, limit, remaining = limiter.check_rate_limit(
        user_id, endpoint="default")

    if not allowed:
        # Calculate reset time (window end)
        reset_time = int(time.time()) + 3600  # 1 hour from now

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


# ============================================================================
# Type Aliases for Dependency Injection
# ============================================================================
# These aliases make endpoint signatures cleaner and more readable.
# Instead of:    user_id: Annotated[str, Depends(get_current_user_id)]
# You can write:  user_id: UserID

UserID = Annotated[str, Depends(get_current_user_id)]
"""Type alias for user ID dependency injection."""

RateLimitCheck = Annotated[None, Depends(check_user_rate_limit)]
"""Type alias for rate limit check dependency injection."""

DatabaseClient = Annotated[SupabaseClient, Depends(get_db)]
"""Type alias for Supabase client dependency injection."""
