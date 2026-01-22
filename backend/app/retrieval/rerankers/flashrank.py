"""
FlashRank local re-ranking implementation.

FlashRank is a fast, lightweight re-ranking library that runs locally on CPU.
It uses cross-encoder models (ms-marco family) for accurate relevance scoring.

Key Features:
- No API calls (runs locally)
- Fast inference on CPU (optimized with ONNX)
- Multiple model sizes (TinyBERT, MiniLM, etc.)
- No GPU required

Performance Characteristics:
- ms-marco-TinyBERT-L-2-v2: ~5ms per query-doc pair (fastest)
- ms-marco-MiniLM-L-6-v2: ~10ms per query-doc pair (balanced)
- ms-marco-MiniLM-L-12-v2: ~20ms per query-doc pair (most accurate)

When to use FlashRank vs Cohere:
- FlashRank: Low latency, privacy-sensitive, high throughput
- Cohere: Best accuracy, willing to pay API costs, internet required
"""

import asyncio
from typing import Any

from flashrank import Ranker, RerankRequest

from app.retrieval.rerankers.base import Reranker
from app.schemas.retrieval import RerankConfig, SearchResult
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FlashRankReranker(Reranker):
    """
    Local CPU-based re-ranking using FlashRank.

    This implementation uses FlashRank's cross-encoder models to re-rank
    search results without making external API calls. It's optimized for
    speed and runs well on CPU.

    Learning Note:
    Cross-encoders vs Bi-encoders:
    - Bi-encoder (retrieval): encode(query) + encode(doc) separately
      - Fast (can pre-compute doc embeddings)
      - Good for initial retrieval (cast wide net)
    - Cross-encoder (re-ranking): encode(query + doc) together
      - Slower (must process each query-doc pair)
      - More accurate (sees full context)
      - Only practical for top-k candidates

    Attributes:
        ranker: FlashRank Ranker instance
        model_name: Name of the model being used
    """

    def __init__(
        self,
        model_name: str = "ms-marco-MiniLM-L-6-v2",
        cache_dir: str | None = None,
    ) -> None:
        """
        Initialize FlashRank reranker.

        Args:
            model_name: Model to use for re-ranking. Options:
                - "ms-marco-TinyBERT-L-2-v2" (fastest, 4MB)
                - "ms-marco-MiniLM-L-6-v2" (balanced, 22MB) [default]
                - "ms-marco-MiniLM-L-12-v2" (best quality, 33MB)
            cache_dir: Directory to cache downloaded models (optional)

        Raises:
            ImportError: If flashrank package is not installed
        """
        self.model_name = model_name
        logger.info(
            "Initializing FlashRank reranker",
            model_name=model_name,
            cache_dir=cache_dir,
        )

        try:
            # Initialize the ranker (downloads model if needed)
            # FlashRank doesn't accept None for cache_dir, so only pass if provided
            if cache_dir:
                self.ranker = Ranker(
                    model_name=model_name,
                    cache_dir=cache_dir,
                )
            else:
                self.ranker = Ranker(model_name=model_name)

            logger.info("FlashRank reranker initialized successfully")

        except ImportError as e:
            logger.error(
                "FlashRank package not installed",
                error=str(e),
            )
            raise ImportError(
                "flashrank package is required. Install with: pip install flashrank"
            ) from e

        except Exception as e:
            logger.error(
                "Failed to initialize FlashRank",
                model_name=model_name,
                error=str(e),
                exc_info=True,
            )
            raise

    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
        config: RerankConfig | None = None,
    ) -> list[SearchResult]:
        """
        Re-rank search results using FlashRank cross-encoder.

        This method:
        1. Validates inputs
        2. Prepares passages for FlashRank
        3. Runs re-ranking in thread pool (CPU-bound)
        4. Updates scores and ranks
        5. Returns top-k results

        Args:
            query: Original search query
            results: Search results to re-rank
            config: Re-ranking configuration (uses defaults if None)

        Returns:
            Re-ranked results with updated scores and ranks

        Example:
            ```python
            reranker = FlashRankReranker(model_name="ms-marco-MiniLM-L-6-v2")
            reranked = await reranker.rerank(
                query="authentication best practices",
                results=initial_results,
                config=RerankConfig(top_k=5)
            )
            # reranked[0] is now the most relevant result
            ```
        """
        # Validate inputs
        self._validate_inputs(query, results)

        if not results:
            return []

        # Use default config if not provided
        if config is None:
            config = RerankConfig()

        logger.info(
            "Re-ranking with FlashRank",
            query=query,
            input_count=len(results),
            top_k=config.top_k,
            model=self.model_name,
        )

        try:
            # Step 1: Prepare passages for FlashRank
            # FlashRank expects a list of dicts with "id" and "text"
            passages = [
                {
                    "id": idx,
                    "text": result.content,
                    "meta": {
                        "chunk_id": str(result.chunk_id),
                        "document_id": str(result.document_id),
                        "original_score": result.score,
                        "original_rank": result.rank,
                        "source": result.source,
                        "metadata": result.metadata,
                    },
                }
                for idx, result in enumerate(results)
            ]

            # Step 2: Create rerank request
            rerank_request = RerankRequest(
                query=query,
                passages=passages,
            )

            # Step 3: Run re-ranking in thread pool (CPU-bound operation)
            logger.debug("Running FlashRank inference")
            reranked_passages = await asyncio.to_thread(
                self.ranker.rerank,
                rerank_request,
            )

            # Step 4: Convert back to SearchResult with new scores
            reranked_results: list[SearchResult] = []

            for passage in reranked_passages[: config.top_k]:
                meta = passage.get("meta", {})
                reranked_results.append(
                    SearchResult(
                        chunk_id=meta["chunk_id"],
                        document_id=meta["document_id"],
                        content=passage["text"],
                        metadata=meta.get("metadata", {}),
                        score=passage["score"],  # FlashRank score (0-1)
                        rank=len(reranked_results) + 1,
                        source="reranked",  # Mark as re-ranked
                    )
                )

            logger.info(
                "Re-ranking complete",
                query=query,
                output_count=len(reranked_results),
            )

            return reranked_results

        except Exception as e:
            # Graceful fallback: return original results if reranking fails
            logger.error(
                "FlashRank re-ranking failed, returning original results",
                query=query,
                error=str(e),
                exc_info=True,
            )

            # Return original results limited to top_k
            return results[: config.top_k]

    def get_model_info(self) -> dict[str, Any]:
        """
        Get information about the loaded model.

        Returns:
            Dictionary with model metadata
        """
        return {
            "model_name": self.model_name,
            "type": "cross-encoder",
            "backend": "flashrank",
            "local": True,
            "gpu_required": False,
        }
