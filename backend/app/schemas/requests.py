"""
Request schemas for API endpoints.

This module defines all request models for the Integration Forge API,
including document ingestion and search operations.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.retrieval import SearchConfig


class IngestRequest(BaseModel):
    """
    Request schema for document ingestion endpoint.

    Note: This is used for JSON-based ingestion. For file uploads,
    use the multipart/form-data endpoint with UploadFile.

    Fields:
        user_id: User ID (will be extracted from JWT in Phase 6)
        content: Raw document content
        title: Document title
        source_id: Parent source ID
        metadata: Optional metadata tags
    """
    user_id: str = Field(
        ...,
        description="User ID (Clerk format: user_xxx). Will be extracted from JWT in Phase 6."
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=10_000_000,  # 10MB as text
        description="Raw document content"
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Document title"
    )
    source_id: UUID = Field(
        ...,
        description="Parent source ID"
    )
    metadata: dict[str, str] | None = Field(
        default=None,
        description="Optional metadata (tags, categories, etc.)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "user_2bXYZ123",
                "content": "# LangGraph Tutorial\n\nLangGraph is a library for building...",
                "title": "LangGraph Quick Start",
                "source_id": "550e8400-e29b-41d4-a716-446655440000",
                "metadata": {
                    "tags": "langgraph,tutorial",
                    "category": "getting-started"
                }
            }
        }
    )


class SearchRequest(BaseModel):
    """
    Request schema for search endpoint.

    This is used for standalone search operations (not part of agentic RAG).
    For chat-based retrieval, use ChatRequest instead.

    Fields:
        query: Search query text
        user_id: User ID for RLS filtering
        source_ids: Optional filter by specific sources
        config: Search configuration (top_k, min_similarity, etc.)
    """
    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Search query text"
    )
    user_id: str = Field(
        ...,
        description="User ID for Row-Level Security filtering"
    )
    source_ids: list[UUID] = Field(
        default_factory=list,
        description="Filter search to specific sources (empty = search all)"
    )
    config: SearchConfig = Field(
        default_factory=SearchConfig,
        description="Search configuration parameters"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "How do I integrate Clerk with Prisma?",
                "user_id": "user_2bXYZ123",
                "source_ids": [],
                "config": {
                    "top_k": 10,
                    "min_similarity": 0.7,
                    "text_rank_function": "ts_rank_cd",
                    "hybrid_alpha": 0.5
                }
            }
        }
    )
