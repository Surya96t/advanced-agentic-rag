"""API Data Transfer Objects (DTOs)."""

# Base schemas
from app.schemas.base import BaseSchema, TimestampSchema

# Chat schemas (Agentic RAG)
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
)

# Document schemas
from app.schemas.document import (
    DocumentDeleteResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentUpdateRequest,
    DocumentUploadRequest,
    DocumentUploadResponse,
)

# Event schemas (SSE streaming)
from app.schemas.events import (
    AgentCompleteEvent,
    AgentStartEvent,
    CitationEvent,
    EndEvent,
    ProgressEvent,
    SSEEventType,
    TokenEvent,
    ValidationEvent,
)

# Request schemas
from app.schemas.requests import (
    IngestRequest,
    SearchRequest,
)

# Response schemas
from app.schemas.responses import (
    ErrorResponse,
    HealthCheckResponse,
    IngestResponse,
    SearchResponse,
)

# Retrieval schemas
from app.schemas.retrieval import (
    SearchConfig,
    SearchResult,
)

__all__ = [
    # Base
    "BaseSchema",
    "TimestampSchema",
    # Documents
    "DocumentUploadRequest",
    "DocumentResponse",
    "DocumentUpdateRequest",
    "DocumentUploadResponse",
    "DocumentListResponse",
    "DocumentDeleteResponse",
    # Requests
    "IngestRequest",
    "SearchRequest",
    # Responses
    "ErrorResponse",
    "HealthCheckResponse",
    "IngestResponse",
    "SearchResponse",
    # Retrieval
    "SearchConfig",
    "SearchResult",
    # Events (SSE)
    "SSEEventType",
    "AgentStartEvent",
    "AgentCompleteEvent",
    "CitationEvent",
    "TokenEvent",
    "ProgressEvent",
    "ValidationEvent",
    "EndEvent",
    # Chat (Agentic RAG)
    "ChatRequest",
    "ChatResponse",
    "FeedbackRequest",
]
