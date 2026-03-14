"""
Rate limit status endpoint.

Returns the current rate limit state for all endpoints for the authenticated user.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import UserID
from app.core.config import settings
from app.core.rate_limiter import get_rate_limiter
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/rate-limit", tags=["rate-limit"])


class EndpointLimitStatus(BaseModel):
    """Rate limit status for a single endpoint."""

    limit: int
    remaining: int
    reset: int


class RateLimitStatusResponse(BaseModel):
    """Rate limit status for all endpoints."""

    chat: EndpointLimitStatus
    ingest: EndpointLimitStatus
    documents: EndpointLimitStatus
    enabled: bool


@router.get(
    "/status",
    response_model=RateLimitStatusResponse,
    summary="Get rate limit status",
    description="Returns current rate limit counts and resets for all endpoints for the authenticated user.",
)
def get_rate_limit_status(user_id: UserID) -> RateLimitStatusResponse:
    """
    Return rate limit status for all endpoints for the current user.

    This endpoint does NOT consume a rate limit slot — it is purely informational.

    Args:
        user_id: Current user ID (injected via dependency)

    Returns:
        RateLimitStatusResponse with per-endpoint limit/remaining/reset values
    """
    logger.info("Rate limit status requested", extra={"user_id": user_id})

    if not settings.rate_limit_enabled:
        disabled = EndpointLimitStatus(limit=0, remaining=0, reset=0)
        return RateLimitStatusResponse(
            chat=disabled,
            ingest=disabled,
            documents=disabled,
            enabled=False,
        )

    limiter = get_rate_limiter()

    # Sentinel returned by peek_rate_limit when Redis is unavailable.
    _UNAVAILABLE = EndpointLimitStatus(limit=-1, remaining=-1, reset=-1)  # noqa: N806

    def _peek(endpoint: str) -> EndpointLimitStatus:
        result = limiter.peek_rate_limit(user_id, endpoint)
        if result is None:
            logger.warning(
                "Redis unavailable during rate limit peek",
                extra={"endpoint": endpoint},
            )
            return _UNAVAILABLE
        limit, remaining, reset = result
        return EndpointLimitStatus(limit=limit, remaining=remaining, reset=reset)

    return RateLimitStatusResponse(
        chat=_peek("chat"),
        ingest=_peek("ingest"),
        documents=_peek("documents"),
        enabled=True,
    )

