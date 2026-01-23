"""
Response schemas for API endpoints.

This module defines all response models for the Integration Forge API,
including health checks, errors, and search results.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.base import utc_now
from app.schemas.retrieval import SearchResult


class HealthCheckResponse(BaseModel):
    """
    Response schema for health check endpoint.

    Used by monitoring systems and load balancers to verify service health.

    Fields:
        status: Service status ("ok" or "degraded")
        timestamp: When the check was performed
        version: API version
        database: Database connection status
    """
    status: str = Field(
        ...,
        description="Service status (ok/degraded/down)"
    )
    timestamp: datetime = Field(
        default_factory=utc_now,
        description="Health check timestamp (UTC)"
    )
    version: str = Field(
        default="1.0.0",
        description="API version"
    )
    database: str = Field(
        ...,
        description="Database connection status (connected/disconnected)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "ok",
                "timestamp": "2026-01-22T10:30:00Z",
                "version": "1.0.0",
                "database": "connected"
            }
        }
    )


class ErrorResponse(BaseModel):
    """
    Standard error response schema.

    All API errors follow this format for consistency.

    Fields:
        error: Error type/class name
        message: Human-readable error message
        status_code: HTTP status code
        details: Optional error details (validation errors, stack trace, etc.)
        request_id: Optional request ID for debugging
    """
    error: str = Field(
        ...,
        description="Error type or class name"
    )
    message: str = Field(
        ...,
        description="Human-readable error message"
    )
    status_code: int = Field(
        ...,
        ge=400,
        le=599,
        description="HTTP status code"
    )
    details: dict | None = Field(
        default=None,
        description="Additional error details (validation errors, etc.)"
    )
    request_id: str | None = Field(
        default=None,
        description="Request ID for debugging (if available)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "error": "ValidationError",
                    "message": "Invalid file type. Allowed extensions: .md, .pdf, .txt",
                    "status_code": 400,
                    "details": {"field": "file", "allowed_types": [".md", ".pdf", ".txt"]},
                    "request_id": "req_abc123"
                },
                {
                    "error": "AuthenticationError",
                    "message": "Invalid or expired JWT token",
                    "status_code": 401,
                    "details": None,
                    "request_id": "req_def456"
                }
            ]
        }
    )


class IngestResponse(BaseModel):
    """
    Response schema for document ingestion endpoint.

    Returns the created document record after successful ingestion.

    Fields:
        document_id: UUID of the created document
        title: Document title
        status: Processing status
        chunks_created: Number of chunks created
        message: Success message
    """
    document_id: str = Field(
        ...,
        description="UUID of the created document"
    )
    title: str = Field(
        ...,
        description="Document title"
    )
    status: str = Field(
        ...,
        description="Processing status (pending/processing/completed/failed)"
    )
    chunks_created: int = Field(
        ge=0,
        description="Number of chunks created during ingestion"
    )
    message: str = Field(
        default="Document ingested successfully",
        description="Success message"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "document_id": "660e8400-e29b-41d4-a716-446655440001",
                "title": "LangGraph Quick Start",
                "status": "completed",
                "chunks_created": 42,
                "message": "Document ingested successfully"
            }
        }
    )


class SearchResponse(BaseModel):
    """
    Response schema for search endpoint.

    Returns search results with metadata about the search operation.

    Fields:
        results: Array of search results
        query: Original search query
        total_results: Total number of results found
        search_type: Type of search performed (vector/text/hybrid)
        execution_time_ms: Search execution time in milliseconds
    """
    results: list[SearchResult] = Field(
        default_factory=list,
        description="Array of search results"
    )
    query: str = Field(
        ...,
        description="Original search query"
    )
    total_results: int = Field(
        ge=0,
        description="Total number of results found"
    )
    search_type: str = Field(
        ...,
        description="Type of search performed (vector/text/hybrid)"
    )
    execution_time_ms: int = Field(
        ge=0,
        description="Search execution time in milliseconds"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "results": [
                    {
                        "chunk_id": "550e8400-e29b-41d4-a716-446655440000",
                        "document_id": "660e8400-e29b-41d4-a716-446655440001",
                        "content": "To integrate Clerk with Prisma, first install both packages...",
                        "metadata": {"section": "Authentication", "page": 1},
                        "score": 0.89,
                        "rank": 1,
                        "source": "hybrid"
                    }
                ],
                "query": "How do I integrate Clerk with Prisma?",
                "total_results": 1,
                "search_type": "hybrid",
                "execution_time_ms": 145
            }
        }
    )
