"""
Server-Sent Events (SSE) schemas for agent streaming.

This module defines all event types emitted during agentic RAG execution,
enabling real-time progress updates via SSE streaming.
"""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import ConfigDict, Field

from app.schemas.base import BaseSchema, utc_now


class SSEEventType(str, Enum):
    """Types of SSE events emitted by the agent."""

    AGENT_START = "agent_start"
    AGENT_COMPLETE = "agent_complete"
    AGENT_ERROR = "agent_error"
    CITATION = "citation"
    TOKEN = "token"
    PROGRESS = "progress"
    VALIDATION = "validation"
    END = "end"


class AgentStartEvent(BaseSchema):
    """Event emitted when an agent node starts execution."""

    agent: str = Field(...,
                       description="Name of the agent node (router, retriever, etc.)")
    message: str = Field(..., description="Human-readable status message")
    timestamp: datetime = Field(
        default_factory=utc_now, description="Event timestamp (UTC)")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "agent": "router",
                    "message": "Analyzing query complexity...",
                    "timestamp": "2026-01-22T10:30:00Z"
                }
            ]
        }
    )


class AgentCompleteEvent(BaseSchema):
    """Event emitted when an agent node completes execution."""

    agent: str = Field(..., description="Name of the agent node")
    result: dict = Field(default_factory=dict,
                         description="Summary of node results")
    next_node: str | None = Field(
        None, description="Next node to execute (if known)")
    timestamp: datetime = Field(
        default_factory=utc_now, description="Event timestamp (UTC)")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "agent": "router",
                    "result": {"query_complexity": "complex"},
                    "next_node": "query_expander",
                    "timestamp": "2026-01-22T10:30:01Z"
                }
            ]
        }
    )


class AgentErrorEvent(BaseSchema):
    """Event emitted when an agent node encounters an error."""

    agent: str = Field(...,
                       description="Name of the agent node that encountered the error")
    error: str = Field(..., description="Error message or description")
    error_code: str | None = Field(
        None, description="Optional error code for categorization")
    recoverable: bool = Field(
        default=False, description="Whether the error is recoverable")
    timestamp: datetime = Field(
        default_factory=utc_now, description="Event timestamp (UTC)")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "agent": "retriever",
                    "error": "Database connection timeout",
                    "error_code": "DB_TIMEOUT",
                    "recoverable": True,
                    "timestamp": "2026-01-22T10:30:05Z"
                },
                {
                    "agent": "generator",
                    "error": "OpenAI API rate limit exceeded",
                    "error_code": "RATE_LIMIT",
                    "recoverable": False,
                    "timestamp": "2026-01-22T10:32:15Z"
                }
            ]
        }
    )


class CitationEvent(BaseSchema):
    """Event emitted when a document chunk is retrieved."""

    chunk_id: UUID = Field(..., description="Chunk UUID")
    document_title: str = Field(..., description="Source document title")
    score: float = Field(..., ge=0.0, le=1.0,
                         description="Relevance score (0.0 to 1.0)")
    source: str = Field(...,
                        description="Search method (vector/text/hybrid/reranked)")
    preview: str | None = Field(
        None, max_length=200, description="Preview of chunk content")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "chunk_id": "550e8400-e29b-41d4-a716-446655440000",
                    "document_title": "Clerk Authentication Guide",
                    "score": 0.89,
                    "source": "reranked",
                    "preview": "To integrate Clerk with your application, first install the package..."
                }
            ]
        }
    )


class TokenEvent(BaseSchema):
    """Event emitted for each LLM token during generation."""

    token: str = Field(..., description="Text token")
    model: str | None = Field(None, description="LLM model name")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "token": "To",
                    "model": "gpt-4"
                }
            ]
        }
    )


class ProgressEvent(BaseSchema):
    """Event emitted to show progress of long-running operations."""

    message: str = Field(..., description="Progress message")
    progress: float = Field(..., ge=0.0, le=1.0,
                            description="Progress percentage (0.0 to 1.0)")
    step: str | None = Field(None, description="Current step name")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "message": "Searching 3 queries...",
                    "progress": 0.4,
                    "step": "retrieval"
                }
            ]
        }
    )


class ValidationEvent(BaseSchema):
    """Event emitted after response validation."""

    passed: bool = Field(..., description="Whether validation passed")
    score: float = Field(..., ge=0.0, le=1.0, description="Quality score")
    issues: list[str] = Field(default_factory=list,
                              description="Validation issues found")
    retry: bool = Field(
        default=False, description="Whether retry will be attempted")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "passed": True,
                    "score": 0.87,
                    "issues": [],
                    "retry": False
                },
                {
                    "passed": False,
                    "score": 0.62,
                    "issues": ["Missing source attribution", "Low retrieval confidence"],
                    "retry": True
                }
            ]
        }
    )


class EndEvent(BaseSchema):
    """Event emitted when agent execution completes."""

    done: bool = Field(default=True, description="Execution complete")
    total_time_ms: int | None = Field(
        None, ge=0, description="Total execution time in milliseconds")
    token_count: int | None = Field(
        None, ge=0, description="Total tokens used")

    # Additional fields for error handling and thread tracking
    thread_id: str | UUID | None = Field(
        None, description="Thread ID for the conversation")
    success: bool = Field(
        default=True, description="Whether execution completed successfully")
    error: str | None = Field(
        None, description="Error message if execution failed")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "done": True,
                    "total_time_ms": 3240,
                    "token_count": 1850,
                    "thread_id": "550e8400-e29b-41d4-a716-446655440000",
                    "success": True,
                    "error": None
                },
                {
                    "done": True,
                    "total_time_ms": 0,
                    "token_count": 0,
                    "thread_id": "invalid",
                    "success": False,
                    "error": "Invalid thread_id format"
                }
            ]
        }
    )
