"""
Feedback repository for handling database operations.
"""

from typing import List
from uuid import UUID

from supabase import Client

from app.schemas.feedback import FeedbackCreate, FeedbackResponse
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FeedbackRepository:
    """
    Repository for handling feedback data operations.
    """

    def __init__(self, client: Client):
        self.client = client
        self.table_name = "feedback"

    def create(self, feedback: FeedbackCreate, user_id: str) -> FeedbackResponse:
        """
        Create a new feedback entry.

        Args:
            feedback: The validated feedback data
            user_id: The authenticated user's ID

        Returns:
            The created feedback response
        """
        # Prepare data for insertion
        data = feedback.model_dump()
        data["user_id"] = user_id
        
        # Insert into Supabase
        # Note: id and created_at are handled by database defaults
        response = self.client.table(self.table_name).insert(data).execute()
        
        if not response.data:
            raise Exception("Failed to create feedback entry")
            
        return FeedbackResponse(**response.data[0])

    def get_by_user(self, user_id: str) -> List[FeedbackResponse]:
        """
        Get all feedback submitted by a specific user.

        Args:
            user_id: The user ID to filter by

        Returns:
            List of Feedback objects
        """
        response = self.client.table(self.table_name)\
            .select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .execute()

        return [FeedbackResponse(**item) for item in response.data]

