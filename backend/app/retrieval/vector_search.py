"""
Vector search implementation using pgvector and OpenAI embeddings.

This module provides semantic search capabilities using dense vector embeddings
and cosine similarity. It leverages the existing HNSW index for fast retrieval.
"""

from typing import Any
from uuid import UUID

from supabase import Client

from app.ingestion.embeddings import EmbeddingClient
from app.schemas.retrieval import SearchConfig, SearchResult
from app.utils.errors import DatabaseError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class VectorSearcher:
    """
    Semantic search using dense vector embeddings.

    This class performs vector similarity search using:
    - OpenAI embeddings (text-embedding-3-small, 1536 dimensions)
    - pgvector cosine similarity
    - HNSW index for fast approximate nearest neighbor search

    Learning Note:
    Vector search is best for:
    - Semantic/conceptual similarity ("auth" matches "authentication", "login")
    - Multilingual queries (embeddings capture meaning across languages)
    - Handling typos (embeddings are robust to small variations)

    Vector search struggles with:
    - Exact keyword matches (use text search)
    - Rare/specific terms (not in training data)
    - Very short queries (<3 words)

    Attributes:
        db: Supabase client instance
        embedder: OpenAI embedding client
    """

    def __init__(
        self,
        db: Client,
        embedder: EmbeddingClient,
    ) -> None:
        """
        Initialize vector searcher.

        Args:
            db: Supabase client instance
            embedder: OpenAI embedding client
        """
        self.db = db
        self.embedder = embedder

    async def search(
        self,
        query: str,
        user_id: str,
        config: SearchConfig | None = None,
    ) -> list[SearchResult]:
        """
        Perform semantic vector search.

        This method:
        1. Generates embedding for the query
        2. Searches for similar chunks using cosine similarity
        3. Filters by user_id (RLS enforcement)
        4. Applies similarity threshold
        5. Returns top-k results

        Args:
            query: Search query text
            user_id: User ID for RLS filtering
            config: Search configuration (uses defaults if None)

        Returns:
            List of SearchResult models ordered by similarity (descending)

        Raises:
            DatabaseError: If search operation fails

        Example:
            ```python
            searcher = VectorSearcher(db, embedder)
            results = await searcher.search(
                query="How do I authenticate users?",
                user_id="user_123",
                config=SearchConfig(top_k=10, min_similarity=0.7)
            )
            for result in results:
                print(f"{result.rank}. {result.content[:100]}... (score: {result.score})")
            ```
        """
        # Use default config if not provided
        if config is None:
            config = SearchConfig()

        logger.info(
            "Performing vector search",
            query=query,
            user_id=user_id,
            top_k=config.top_k,
            min_similarity=config.min_similarity,
        )

        try:
            # Step 1: Generate query embedding
            logger.debug("Generating query embedding")
            query_embedding = await self.embedder.embed_single(query)

            # Step 2: Call stored procedure for vector search
            # Uses the search_chunks_by_embedding() function from migration 001
            logger.debug("Executing vector search query")

            result = self.db.rpc(
                "search_chunks_by_embedding",
                {
                    "query_embedding": query_embedding,
                    "match_count": config.top_k,
                    "filter_user_id": user_id,
                }
            ).execute()

            # Step 3: Parse results
            if not result.data:
                logger.info("No results found", query=query)
                return []

            # Step 4: Filter by similarity threshold and convert to SearchResult
            search_results: list[SearchResult] = []
            rank = 1

            for row in result.data:
                similarity = row.get("similarity", 0.0)

                # Apply minimum similarity threshold
                if similarity < config.min_similarity:
                    logger.debug(
                        "Skipping result below threshold",
                        similarity=similarity,
                        threshold=config.min_similarity,
                    )
                    continue

                search_results.append(
                    SearchResult(
                        chunk_id=UUID(row["id"]),
                        document_id=UUID(row["document_id"]),
                        content=row["content"],
                        metadata=row.get("metadata", {}),
                        score=similarity,
                        rank=rank,
                        source="vector",
                    )
                )
                rank += 1

            logger.info(
                "Vector search complete",
                query=query,
                results_count=len(search_results),
            )

            return search_results

        except Exception as e:
            logger.error(
                "Vector search failed",
                query=query,
                error=str(e),
                exc_info=True,
            )
            raise DatabaseError(
                message="Failed to perform vector search",
                details={
                    "error": str(e),
                    "query": query,
                },
            )

    async def search_by_embedding(
        self,
        embedding: list[float],
        user_id: str,
        config: SearchConfig | None = None,
    ) -> list[SearchResult]:
        """
        Search using a pre-computed embedding vector.

        This is useful when you already have an embedding (e.g., from another source)
        and want to skip the embedding generation step.

        Args:
            embedding: Pre-computed embedding vector (1536 dimensions)
            user_id: User ID for RLS filtering
            config: Search configuration (uses defaults if None)

        Returns:
            List of SearchResult models ordered by similarity (descending)

        Raises:
            DatabaseError: If search operation fails
            ValueError: If embedding dimensions don't match (not 1536)
        """
        # Validate embedding dimensions
        if len(embedding) != 1536:
            raise ValueError(
                f"Invalid embedding dimensions: {len(embedding)}. "
                "Expected 1536 for text-embedding-3-small"
            )

        # Use default config if not provided
        if config is None:
            config = SearchConfig()

        logger.info(
            "Performing vector search with pre-computed embedding",
            user_id=user_id,
            top_k=config.top_k,
            min_similarity=config.min_similarity,
        )

        try:
            # Call stored procedure with embedding
            result = self.db.rpc(
                "search_chunks_by_embedding",
                {
                    "query_embedding": embedding,
                    "match_count": config.top_k,
                    "filter_user_id": user_id,
                }
            ).execute()

            # Parse and filter results
            if not result.data:
                logger.info("No results found")
                return []

            search_results: list[SearchResult] = []
            rank = 1

            for row in result.data:
                similarity = row.get("similarity", 0.0)

                if similarity < config.min_similarity:
                    continue

                search_results.append(
                    SearchResult(
                        chunk_id=UUID(row["id"]),
                        document_id=UUID(row["document_id"]),
                        content=row["content"],
                        metadata=row.get("metadata", {}),
                        score=similarity,
                        rank=rank,
                        source="vector",
                    )
                )
                rank += 1

            logger.info(
                "Vector search complete",
                results_count=len(search_results),
            )

            return search_results

        except Exception as e:
            logger.error(
                "Vector search failed",
                error=str(e),
                exc_info=True,
            )
            raise DatabaseError(
                message="Failed to perform vector search",
                details={"error": str(e)},
            )
