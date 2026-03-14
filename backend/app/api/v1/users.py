"""
User management API endpoints.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from app.api.deps import UserID
from app.database.client import get_db
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/users", tags=["users"])


class UserSyncRequest(BaseModel):
    """Request to sync user from Clerk to Supabase."""
    user_id: str = Field(...,
                         description="Clerk user ID (e.g., user_2bXYZ123)")
    email: EmailStr = Field(..., description="User email address")
    full_name: str = Field(..., description="User full name")


class UserSyncResponse(BaseModel):
    """Response after syncing user."""
    user_id: str
    email: str
    full_name: str
    created: bool


@router.post(
    "/sync",
    response_model=UserSyncResponse,
    summary="Sync user from Clerk to Supabase",
    description="Create or update user in Supabase users table",
)
async def sync_user(request: UserSyncRequest, current_user_id: UserID) -> UserSyncResponse:
    """
    Sync user from Clerk to Supabase.

    Requires a valid Clerk JWT. The user_id in the request body must match
    the authenticated user's ID to prevent one user from overwriting another's record.

    Args:
        request: User sync request with Clerk user data
        current_user_id: Authenticated user ID from JWT (injected)

    Returns:
        UserSyncResponse with user data and created flag

    Raises:
        HTTPException: 403 if request.user_id does not match the JWT
        HTTPException: 500 if database error occurs
    """
    if request.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot sync a user record other than your own.",
        )

    logger.info(
        "Syncing user to database",
        extra={"user_id": request.user_id}
    )

    try:
        supabase = get_db()

        # Check if user already exists
        existing_user = supabase.table("users").select(
            "id").eq("id", request.user_id).execute()
        created = len(existing_user.data or []) == 0

        # Upsert user (insert if new, update if exists)
        # Note: 'id' is the column name in the users table (not 'user_id')
        supabase.table("users").upsert({
            "id": request.user_id,
            "email": request.email,
            "full_name": request.full_name,
        }, on_conflict="id").execute()

        logger.info(
            "User synced successfully",
            extra={
                "user_id": request.user_id,
                "created": created
            }
        )

        return UserSyncResponse(
            user_id=request.user_id,
            email=request.email,
            full_name=request.full_name,
            created=created,
        )

    except Exception as e:
        logger.error(
            "Failed to sync user",
            extra={"user_id": request.user_id, "error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync user: {str(e)}"
        )
