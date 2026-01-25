"""
Shared dependencies for API routes.

This module provides dependency injection functions for FastAPI endpoints,
including user authentication and rate limiting.

Phase 5: Uses hardcoded user_id for testing without authentication
Phase 6: Will implement Clerk JWT validation and Redis-based rate limiting
"""

from typing import Annotated

from fastapi import Depends

from app.database.client import SupabaseClient, get_db


def get_current_user_id() -> str:
    """
    Get current user ID.

    Phase 5: Returns hardcoded test user ID for testing without authentication.
             This allows testing all endpoints with curl/httpie/browser before
             implementing JWT validation.

    Phase 6: Will validate JWT token from Authorization header and extract
             user_id from the 'sub' claim (Clerk format: "user_2bXYZ123")

    Returns:
        User ID string (Clerk-compatible format)

    Example:
        ```python
        @router.get("/documents")
        def list_documents(user_id: UserID):
            # user_id will be "test_user_phase5" in Phase 5
            documents = document_repo.list_by_user(user_id)
            return documents
        ```
    """
    return "test_user_phase5"


async def check_user_rate_limit(
    user_id: Annotated[str, Depends(get_current_user_id)]
) -> None:
    """
    Check if current user has exceeded rate limit.

    Phase 5: No-op function - rate limiting is disabled for testing.
             This allows unlimited requests during development.

    Phase 6: Will implement Redis-based sliding window rate limiter with:
             - 100 requests per hour per user
             - Burst allowance for short spikes
             - HTTPException 429 if limit exceeded

    Args:
        user_id: Current user's ID (injected via dependency)

    Raises:
        HTTPException: 429 Too Many Requests if limit exceeded (Phase 6)

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
    # TODO: Implement in Phase 6
    # from app.core.rate_limiter import check_rate_limit
    # if not check_rate_limit(user_id):
    #     raise HTTPException(status_code=429, detail="Rate limit exceeded")
    pass


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
