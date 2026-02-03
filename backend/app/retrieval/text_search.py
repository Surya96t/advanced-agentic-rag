"""
Text search implementation using PostgreSQL full-text search.

This module provides keyword-based search capabilities using PostgreSQL's
native full-text search (tsvector/tsquery) and the GIN index.
"""

from uuid import UUID

from supabase import Client

from app.schemas.retrieval import SearchConfig, SearchResult
from app.utils.errors import DatabaseError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TextSearcher:
    """
    Keyword/lexical search using PostgreSQL full-text search.

    This class performs text search using:
    - PostgreSQL tsvector/tsquery
    - GIN index for fast lookup
    - ts_rank or ts_rank_cd for relevance scoring

    Learning Note:
    Text search is best for:
    - Exact keyword matches ("authentication" must appear)
    - Rare/specific terms (product names, API names)
    - Short queries (1-2 words)
    - Boolean logic (AND/OR combinations)

    Text search struggles with:
    - Semantic similarity (won't match "auth" with "login")
    - Typos (unless using fuzzy matching)
    - Multilingual queries (English dictionary only)

    How it works:
    1. Query is converted to tsquery (handles stemming, stopwords)
    2. tsquery is matched against search_vector column (GIN indexed)
    3. Results are ranked using ts_rank or ts_rank_cd
    4. Top-k results returned

    Attributes:
        db: Supabase client instance
    """

    def __init__(self, db: Client) -> None:
        """
        Initialize text searcher.

        Args:
            db: Supabase client instance
        """
        self.db = db

    async def search(
        self,
        query: str,
        user_id: str,
        config: SearchConfig | None = None,
    ) -> list[SearchResult]:
        """
        Perform full-text keyword search.

        This method:
        1. Converts query to tsquery (auto-handles stemming, stopwords)
        2. Searches search_vector column using GIN index
        3. Ranks results using ts_rank or ts_rank_cd
        4. Filters by user_id (RLS enforcement)
        5. Returns top-k results

        Args:
            query: Search query text (can include AND/OR but not required)
            user_id: User ID for RLS filtering
            config: Search configuration (uses defaults if None)

        Returns:
            List of SearchResult models ordered by relevance (descending)

        Raises:
            DatabaseError: If search operation fails

        Example:
            ```python
            searcher = TextSearcher(db)
            results = searcher.search(
                query="authentication oauth",
                user_id="user_123",
                config=SearchConfig(top_k=10)
            )
            for result in results:
                print(f"{result.rank}. {result.content[:100]}... (score: {result.score})")
            ```

        Learning Note: Query Processing
        - "auth setup" → plainto_tsquery → 'auth' & 'setup'
        - Automatically handles: stemming (running → run), stopwords (the, a)
        - For boolean: "auth AND oauth" works, but not required
        - Phrase search: Use quotes in future (not implemented yet)
        """
        # Use default config if not provided
        if config is None:
            config = SearchConfig()

        logger.info(
            "Performing text search",
            query=query,
            user_id=user_id,
            top_k=config.top_k,
            rank_function=config.text_rank_function,
        )

        try:
            # Call stored procedure for text search
            # Uses the search_chunks_by_text() function from migration 004
            import time
            start_db = time.time()
            logger.debug("Executing text search query")

            result = self.db.rpc(
                "search_chunks_by_text",
                {
                    "query_text": query,
                    "match_count": config.top_k,
                    "filter_user_id": user_id,
                    "ranking_function": config.text_rank_function,
                }
            ).execute()
            db_time = time.time() - start_db
            logger.info(f"Text search database query took {db_time:.2f}s")

            # Parse results
            if not result.data:
                logger.info("No results found", query=query)
                return []

            # Convert to SearchResult
            search_results: list[SearchResult] = []
            rank = 1

            for row in result.data:
                # Text search rank is already a score (higher = better)
                # No minimum threshold for text search (rank varies widely)
                text_rank = row.get("rank", 0.0)

                search_results.append(
                    SearchResult(
                        chunk_id=UUID(row["id"]),
                        document_id=UUID(row["document_id"]),
                        document_title=row.get(
                            "document_title", "Unknown Document"),
                        content=row["content"],
                        metadata=row.get("metadata", {}),
                        score=text_rank,
                        original_score=text_rank,  # Preserve original text rank
                        rank=rank,
                        source="text",
                    )
                )
                rank += 1

            logger.info(
                "Text search complete",
                query=query,
                results_count=len(search_results),
            )

            return search_results

        except Exception as e:
            logger.error(
                "Text search failed",
                query=query,
                error=str(e),
                exc_info=True,
            )
            raise DatabaseError(
                message="Failed to perform text search",
                details={
                    "error": str(e),
                    "query": query,
                },
            )

    def search_with_filters(
        self,
        query: str,
        user_id: str,
        document_ids: list[UUID] | None = None,
        metadata_filters: dict | None = None,
        config: SearchConfig | None = None,
    ) -> list[SearchResult]:
        """
        Perform text search with additional filters.

        This allows filtering by document IDs or metadata fields
        in addition to the text search.

        Args:
            query: Search query text
            user_id: User ID for RLS filtering
            document_ids: Optional list of document IDs to search within
            metadata_filters: Optional JSONB metadata filters
            config: Search configuration (uses defaults if None)

        Returns:
            List of SearchResult models ordered by relevance (descending)

        Raises:
            DatabaseError: If search operation fails

        Example:
            ```python
            # Search only in specific documents
            results = searcher.search_with_filters(
                query="authentication",
                user_id="user_123",
                document_ids=[doc_id_1, doc_id_2],
            )

            # Search with metadata filter (e.g., only TypeScript code)
            results = searcher.search_with_filters(
                query="auth function",
                user_id="user_123",
                metadata_filters={"language": "typescript"},
            )
            ```
        """
        # Use default config if not provided
        if config is None:
            config = SearchConfig()

        logger.info(
            "Performing text search with filters",
            query=query,
            user_id=user_id,
            document_ids_count=len(document_ids) if document_ids else 0,
            has_metadata_filters=metadata_filters is not None,
        )

        try:
            # Build custom query with filters
            # Note: For now, we'll use basic search and filter in Python
            # In production, consider a custom stored procedure for this

            # Get initial results
            results = self.search(query, user_id, config)

            # Apply document_id filter
            if document_ids:
                results = [
                    r for r in results
                    if r.document_id in document_ids
                ]

            # Apply metadata filters
            if metadata_filters:
                filtered_results = []
                for result in results:
                    # Check if all filter conditions match
                    matches = True
                    for key, value in metadata_filters.items():
                        if result.metadata.get(key) != value:
                            matches = False
                            break
                    if matches:
                        filtered_results.append(result)
                results = filtered_results

            # Re-rank after filtering
            for idx, result in enumerate(results, start=1):
                result.rank = idx

            logger.info(
                "Text search with filters complete",
                query=query,
                results_count=len(results),
            )

            return results

        except Exception as e:
            logger.error(
                "Text search with filters failed",
                query=query,
                error=str(e),
                exc_info=True,
            )
            raise DatabaseError(
                message="Failed to perform text search with filters",
                details={
                    "error": str(e),
                    "query": query,
                },
            )
