"""
Base Pydantic schemas used across the application.

This module defines common models and base classes that are reused
throughout the application for consistent data validation.
"""

from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BaseSchema(BaseModel):
    """
    Base schema with common configuration.

    All Pydantic models should inherit from this class for consistent behavior.
    """

    model_config = ConfigDict(
        # Allow population by field name and alias
        populate_by_name=True,
        # Use enum values instead of enum objects in JSON
        use_enum_values=True,
        # Validate default values
        validate_default=True,
        # Validate on assignment
        validate_assignment=True,
        # Extra fields are forbidden
        extra="forbid",
        # Custom JSON schema configuration
        json_schema_extra={
            "examples": []
        }
    )


class TimestampSchema(BaseSchema):
    """Schema with created_at and updated_at timestamps."""

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the record was created"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the record was last updated"
    )


class UUIDSchema(BaseSchema):
    """Schema with UUID identifier."""

    id: UUID = Field(..., description="Unique identifier")


class TimestampUUIDSchema(UUIDSchema, TimestampSchema):
    """Schema with both UUID and timestamps (most common base)."""

    pass


class PaginationParams(BaseSchema):
    """Query parameters for pagination."""

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of items per page (max 100)"
    )

    @property
    def offset(self) -> int:
        """Calculate offset from page and page_size."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Get limit (alias for page_size)."""
        return self.page_size


T = TypeVar("T")


class PaginatedResponse(BaseSchema, Generic[T]):
    """Generic paginated response wrapper."""

    items: list[T] = Field(..., description="List of items for current page")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        pagination: PaginationParams,
    ) -> "PaginatedResponse[T]":
        """
        Create a paginated response from items and pagination params.

        Args:
            items: List of items for the current page
            total: Total number of items across all pages
            pagination: Pagination parameters

        Returns:
            PaginatedResponse: Paginated response object
        """
        total_pages = (total + pagination.page_size -
                       1) // pagination.page_size

        return cls(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=total_pages,
        )


class ErrorDetail(BaseSchema):
    """Detailed error information."""

    field: str | None = Field(
        default=None, description="Field that caused the error")
    message: str = Field(..., description="Error message")
    code: str | None = Field(default=None, description="Error code")


class ErrorResponse(BaseSchema):
    """Standard error response format."""

    error: str = Field(..., description="Error type or title")
    message: str = Field(..., description="Human-readable error message")
    status_code: int = Field(..., description="HTTP status code")
    details: list[ErrorDetail] | dict[str, Any] = Field(
        default_factory=list,
        description="Additional error details"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the error occurred"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "ValidationError",
                "message": "Invalid input data",
                "status_code": 400,
                "details": [
                    {
                        "field": "email",
                        "message": "Invalid email format",
                        "code": "invalid_email"
                    }
                ],
                "timestamp": "2026-01-19T12:00:00Z"
            }
        }
    )


class SuccessResponse(BaseSchema):
    """Standard success response format."""

    success: bool = Field(default=True, description="Operation success status")
    message: str = Field(..., description="Success message")
    data: dict[str, Any] | None = Field(
        default=None, description="Optional response data")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Document uploaded successfully",
                "data": {
                    "document_id": "550e8400-e29b-41d4-a716-446655440000"
                }
            }
        }
    )


class HealthResponse(BaseSchema):
    """Health check response for API endpoints."""

    status: str = Field(..., description="Service status (healthy/unhealthy)")
    environment: str = Field(..., description="Current environment")
    version: str = Field(..., description="Application version")
    services: dict[str, str] = Field(
        default_factory=dict,
        description="Status of dependent services"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "environment": "development",
                "version": "0.1.0",
                "services": {
                    "database": "healthy",
                    "api": "healthy"
                }
            }
        }
    )


class HealthCheckResponse(BaseSchema):
    """Health check response."""

    status: str = Field(..., description="Service status (healthy/unhealthy)")
    version: str = Field(..., description="Application version")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Health check timestamp"
    )
    services: dict[str, bool] = Field(
        default_factory=dict,
        description="Status of dependent services"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "version": "0.1.0",
                "timestamp": "2026-01-19T12:00:00Z",
                "services": {
                    "database": True,
                    "openai": True,
                    "supabase": True
                }
            }
        }
    )
