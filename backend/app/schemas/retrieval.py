"""
Retrieval schemas for search results and configuration.

This module defines Pydantic models for the retrieval system, including
search results, search configuration, and re-ranking configuration.
"""

from typing import Literal
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema


class SearchResult(BaseSchema):
    """
    Unified search result model for all retrieval methods.

    This model is used by vector search, text search, and hybrid search
    to provide a consistent interface for search results.

    Attributes:
        chunk_id: Unique identifier for the chunk
        document_id: ID of the parent document
        document_title: Title of the parent document
        content: The actual text content of the chunk
        metadata: JSONB metadata (headers, page numbers, language, etc.)
        score: Relevance score (0.0 to 1.0 for vector, varies for text/hybrid)
        original_score: Original score before fusion/reranking (for display)
        rank: Position in the result list (1-indexed)
        source: Which search method produced this result

    Learning Note:
    - Vector search score: cosine similarity (0.0 to 1.0, higher is better)
    - Text search score: ts_rank or ts_rank_cd (varies, higher is better)
    - Hybrid search score: RRF score (0.0 to 0.033, small numbers are normal!)
    - Reranked score: cross-encoder score (0.0 to 1.0, higher is better)
    - Original score: Preserved from vector/text search for user display
    """
    chunk_id: UUID = Field(..., description="Chunk UUID")
    document_id: UUID = Field(..., description="Parent document UUID")
    document_title: str = Field(..., description="Parent document title")
    content: str = Field(..., description="Chunk text content")
    metadata: dict = Field(
        default_factory=dict,
        description="JSONB metadata from chunk"
    )
    score: float = Field(
        ...,
        description="Relevance score (interpretation varies by source)"
    )
    original_score: float | None = Field(
        default=None,
        description="Original cosine similarity or text rank before RRF fusion (for display to users)"
    )
    rank: int = Field(
        ...,
        ge=1,
        description="Position in result list (1-indexed)"
    )
    source: Literal["vector", "text", "hybrid", "reranked"] = Field(
        ...,
        description="Search method that produced this result"
    )


class SearchConfig(BaseSchema):
    """
    Configuration for search operations.

    This model configures parameters for vector search, text search,
    and hybrid search operations.

    Attributes:
        top_k: Number of results to return
        min_similarity: Minimum similarity threshold for vector search
        text_rank_function: Text search ranking function
        hybrid_alpha: Weight for vector vs text search in hybrid mode

    Learning Note:
    - top_k: Typically 5-20 for RAG (more = better recall, slower)
    - min_similarity: 0.7+ recommended for production (filters noise)
    - ts_rank_cd: Better than ts_rank (considers term proximity)
    - hybrid_alpha: 0.5 = balanced, 1.0 = vector only, 0.0 = text only
    """
    top_k: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of chunks to retrieve"
    )
    min_similarity: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity threshold (vector search)"
    )
    text_rank_function: Literal["ts_rank", "ts_rank_cd"] = Field(
        default="ts_rank_cd",
        description="PostgreSQL text ranking function"
    )
    hybrid_alpha: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Weight for vector search in hybrid mode (0=text, 1=vector)"
    )


class RerankConfig(BaseSchema):
    """
    Configuration for re-ranking operations.

    Re-ranking uses a cross-encoder model to re-score and re-order
    the initial search results for better relevance.

    Attributes:
        enabled: Whether to enable re-ranking
        top_k: Number of results to keep after re-ranking
        model: Re-ranking model to use

    Learning Note:
    - Re-ranking improves precision but adds latency (~50-100ms)
    - Typically re-rank top 20-50 results to top 5-10
    - FlashRank: Fast local model (~50ms for 20 chunks)
    - Cohere: Higher quality but requires API call (~100-200ms)
    """
    enabled: bool = Field(
        default=True,
        description="Enable re-ranking"
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Number of results to keep after re-ranking"
    )
    model: Literal["flashrank", "cohere"] = Field(
        default="flashrank",
        description="Re-ranking model to use"
    )
