"""
Chat API schemas for agent interaction.

This module defines request and response models for the agentic RAG chat endpoint,
including support for streaming, feedback, and conversation threading.
"""

from uuid import UUID

from pydantic import ConfigDict, Field

from app.schemas.base import BaseSchema
from app.schemas.retrieval import SearchResult


class ChatRequest(BaseSchema):
    """Request schema for chat endpoint."""

    message: str = Field(
        ..., min_length=1, max_length=2000, description="User's question or prompt"
    )
    thread_id: UUID | None = Field(
        default=None,
        description="Thread ID for conversation continuity (created lazily on first message if not provided)",
    )
    title: str | None = Field(
        default=None,
        max_length=200,
        description="Optional custom title for the thread (only used for new threads)",
    )
    source_ids: list[UUID] = Field(
        default_factory=list,
        description="Filter retrieval to specific source IDs (empty = search all)",
    )
    stream: bool = Field(
        default=True, description="Whether to stream response via SSE (recommended)"
    )
    is_new_thread: bool = Field(
        default=False,
        description="True when the client pre-generated this thread_id and has not sent a message on it before",
    )
    max_retries: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Maximum validation retries before returning best attempt",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "message": "How do I integrate Clerk authentication with Prisma?",
                    "thread_id": None,
                    "source_ids": [],
                    "stream": True,
                    "max_retries": 2,
                }
            ]
        }
    )


class ChatResponse(BaseSchema):
    """Response schema for chat endpoint (non-streaming)."""

    thread_id: UUID | None = Field(None, description="Thread ID for this conversation")
    content: str = Field(..., description="Generated answer")
    sources: list[SearchResult] = Field(
        default_factory=list, description="Retrieved chunks used for generation"
    )
    quality_score: float | None = Field(
        None, ge=0.0, le=1.0, description="Validation quality score"
    )
    metadata: dict = Field(
        default_factory=dict, description="Execution metadata (timing, costs, retries, etc.)"
    )
    validation_passed: bool | None = Field(None, description="Whether quality validation passed")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "thread_id": "550e8400-e29b-41d4-a716-446655440000",
                    "response": "To integrate Clerk with Prisma...",
                    "sources": [],
                    "quality_score": 0.87,
                    "metadata": {
                        "execution_time_ms": 3240,
                        "total_tokens": 1850,
                        "retries": 0,
                        "nodes_executed": [
                            "router",
                            "query_expander",
                            "retriever",
                            "generator",
                            "validator",
                        ],
                    },
                    "validation_passed": True,
                }
            ]
        }
    )


class FeedbackRequest(BaseSchema):
    """User feedback on agent response for human-in-the-loop."""

    thread_id: UUID = Field(..., description="Thread ID of the conversation")
    message_id: UUID = Field(..., description="Message ID being rated")
    rating: int = Field(..., ge=-1, le=1, description="Thumbs up (1), down (-1), or neutral (0)")
    refinement_request: str | None = Field(
        None,
        max_length=500,
        description="Optional refinement instructions (e.g., 'Focus more on TypeScript examples')",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "thread_id": "550e8400-e29b-41d4-a716-446655440000",
                    "message_id": "660e8400-e29b-41d4-a716-446655440001",
                    "rating": -1,
                    "refinement_request": "Please provide more TypeScript examples instead of JavaScript",
                }
            ]
        }
    )
