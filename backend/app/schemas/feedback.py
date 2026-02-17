from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.database.models import FeedbackType


class FeedbackBase(BaseModel):
    """Shared properties for feedback."""
    feedback_type: FeedbackType
    message: str = Field(..., min_length=10, description="Feedback message content")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")


class FeedbackCreate(FeedbackBase):
    """Properties to receive on feedback creation."""
    pass


class FeedbackResponse(FeedbackBase):
    """Properties to return after feedback creation."""
    id: UUID
    user_id: str
    created_at: datetime
    updated_at: datetime | None = None
    
    model_config = ConfigDict(from_attributes=True)

