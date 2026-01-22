"""
Base interface for re-ranking implementations.

Re-ranking is the second stage in a retrieval pipeline:
1. First-stage retrieval: Cast a wide net (retrieve top-100 candidates)
2. Re-ranking: Precisely score and re-order candidates (return top-10)

Why re-rank?
- Retrieval optimizes for recall (find all potentially relevant docs)
- Re-ranking optimizes for precision (rank best docs first)
- Re-ranking is more expensive (cross-encoder vs bi-encoder)
- Only applied to top candidates (cost-effective)

Learning Note:
- Bi-encoder (retrieval): Encodes query and documents separately, fast
- Cross-encoder (re-ranking): Encodes query+document together, accurate but slow
"""

from abc import ABC, abstractmethod

from app.schemas.retrieval import RerankConfig, SearchResult
from app.utils.logger import get_logger

logger = get_logger(__name__)


class Reranker(ABC):
    """
    Abstract base class for re-ranking implementations.

    Re-rankers take a list of search results and re-order them based on
    relevance to the query. They use more sophisticated (and expensive)
    models than the initial retrieval stage.

    Implementations:
    - FlashRank: Fast local CPU-based cross-encoder re-ranking
    - Cohere: Cloud-based re-ranking API (requires API key)
    """

    @abstractmethod
    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
        config: RerankConfig | None = None,
    ) -> list[SearchResult]:
        """
        Re-rank search results based on relevance to the query.

        This method:
        1. Takes initial search results (e.g., from hybrid search)
        2. Computes more accurate relevance scores (cross-encoder)
        3. Re-orders results by new scores
        4. Returns top-k results

        Args:
            query: Original search query
            results: Initial search results to re-rank
            config: Re-ranking configuration (uses defaults if None)

        Returns:
            Re-ranked list of SearchResult, ordered by relevance (descending)
            Scores are updated to reflect re-ranking scores.
            Ranks are updated to reflect new ordering.

        Raises:
            Exception: Implementation-specific errors (should handle gracefully)

        Example:
            ```python
            reranker = FlashRankReranker()
            initial_results = await hybrid_searcher.search(query, user_id)
            reranked = await reranker.rerank(
                query="How do I authenticate users?",
                results=initial_results,
                config=RerankConfig(top_k=5)
            )
            ```
        """
        pass

    def _validate_inputs(
        self,
        query: str,
        results: list[SearchResult],
    ) -> None:
        """
        Validate rerank inputs.

        Args:
            query: Search query
            results: Search results to rerank

        Raises:
            ValueError: If inputs are invalid
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        if not results:
            logger.warning("No results to rerank, returning empty list")

        # Log warning if results list is very large
        if len(results) > 100:
            logger.warning(
                "Re-ranking large result set",
                count=len(results),
                recommendation="Consider limiting initial retrieval to <100 results",
            )

    def _update_ranks(self, results: list[SearchResult]) -> list[SearchResult]:
        """
        Update rank field after re-ordering.

        Args:
            results: Search results (already sorted by score)

        Returns:
            Same results with updated ranks (1, 2, 3, ...)
        """
        for idx, result in enumerate(results, start=1):
            result.rank = idx
        return results
