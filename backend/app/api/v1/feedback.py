"""
API endpoints for user feedback.

This module provides operations for submitting and retrieving user feedback.
"""

from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.api.deps import get_current_user
from app.database.client import get_db
from app.database.repositories.feedback import FeedbackRepository
from app.schemas.base import ErrorResponse
from app.schemas.feedback import FeedbackCreate, FeedbackResponse
from app.utils.logger import get_logger

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])
logger = get_logger(__name__)


@router.post(
    "",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit feedback",
    description="Submit new feedback (bug, feature request, etc.)",
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
def submit_feedback(
    feedback: FeedbackCreate,
    current_user: Annotated[str, Depends(get_current_user)],
    db: Client = Depends(get_db),
) -> FeedbackResponse:
    """
    Submit user feedback.

    Args:
        feedback: Feedback data content
        current_user: The authenticated user ID
        db: Database client

    Returns:
        Created feedback object
    """
    user_id = current_user
    logger.info("Submitting feedback", extra={"user_id": user_id, "type": feedback.feedback_type})

    try:
        repo = FeedbackRepository(db)
        return repo.create(feedback, user_id)
    except Exception as e:
        logger.error("Failed to submit feedback", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to submit feedback"
        )


@router.get(
    "",
    response_model=List[FeedbackResponse],
    status_code=status.HTTP_200_OK,
    summary="Get user feedback",
    description="Get all feedback submitted by the current user",
)
def get_user_feedback(
    current_user: Annotated[str, Depends(get_current_user)],
    db: Client = Depends(get_db),
) -> List[FeedbackResponse]:
    """
    Get all feedback submitted by the current user.

    Args:
        current_user: The authenticated user ID
        db: Database client

    Returns:
        List of feedback objects
    """
    user_id = current_user
    logger.info("Fetching user feedback", extra={"user_id": user_id})

    try:
        repo = FeedbackRepository(db)
        return repo.get_by_user(user_id)
    except Exception as e:
        logger.error("Failed to fetch feedback", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch feedback"
        )
