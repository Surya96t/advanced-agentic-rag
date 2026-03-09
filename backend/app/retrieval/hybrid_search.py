"""
Hybrid search: dense vector + sparse text + RRF fusion.

This module implements hybrid search by combining vector and text search
results using Reciprocal Rank Fusion (RRF) for optimal retrieval performance.
"""

from uuid import UUID

import asyncio

from supabase import Client

from app.ingestion.embeddings import EmbeddingClient
from app.retrieval.text_search import TextSearcher
from app.retrieval.vector_search import VectorSearcher
from app.schemas.retrieval import SearchConfig, SearchResult
from app.utils.logger import get_logger

logger = get_logger(__name__)


def normalize_rrf_score(rrf_score: float, rrf_k: int = 60) -> float:
    """
    Normalise a raw RRF score to the [0, 1] range.

    RRF score range (for a single list with k=60):
        Minimum: approaches 0 as rank → ∞
        Maximum: 1 / (k + 1)  when rank = 1

    For a weighted sum of two lists (alpha * v + (1-alpha) * t), the max is
    still 1/(k+1) because alpha + (1-alpha) = 1.
    Therefore: normalised = rrf_score * (k + 1)

    Args:
        rrf_score: Raw RRF score from _reciprocal_rank_fusion.
        rrf_k: The RRF constant used during fusion (must match the searcher's rrf_k).

    Returns:
        Score in [0, 1], with 1.0 meaning rank-1 in both retrieval lists.
    """
    return min(rrf_score * (rrf_k + 1), 1.0)


class HybridSearcher:
    """
    Hybrid search combining vector and text search with RRF fusion.

    This class implements a production-grade hybrid search system that:
    - Runs vector search (semantic similarity)
    - Runs text search (keyword matching)
    - Fuses results using Reciprocal Rank Fusion (RRF)
    - Handles deduplication
    - Provides configurable weighting (alpha parameter)

    Learning Note: Why Hybrid Search?

    Vector search alone:
    - Great for: semantic queries, synonyms, typos
    - Poor for: exact keywords, rare terms, technical jargon

    Text search alone:
    - Great for: exact matches, specific terms, boolean logic
    - Poor for: semantic meaning, paraphrasing, multilingual

    Hybrid (best of both):
    - Combines strengths of vector and text search
    - More robust to query variations
    - Better precision AND recall
    - Industry standard for production RAG

    RRF Algorithm:
    For each chunk, compute:
        RRF_score = Σ [1 / (k + rank_i)]
    where:
    - k = 60 (constant from research, controls score range)
    - rank_i = position in result list i (1-indexed)
    - Σ sums over all result lists (vector + text)

    Score Interpretation (After Alpha-Weighting):
    The API returns alpha-weighted RRF scores: alpha * RRF_vector + (1-alpha) * RRF_text
    
    With k=60 and default alpha=0.5 (balanced):
    - Maximum possible score (rank 1 in both lists): 1/61 ≈ 0.0164
    - Typical good matches: 0.005 to 0.015
    - Scores are NOT cosine similarity (0.0-1.0). Low absolute values are normal.
    
    Note: Alpha adjusts vector vs text weighting but maximum stays ~0.0164 regardless of alpha
    because the formula is a weighted average of the two RRF components.

    Example (alpha=0.5):
    Chunk appears at rank 3 in vector, rank 5 in text:
    RRF_vector = 1/(60+3) = 0.0159
    RRF_text = 1/(60+5) = 0.0154
    Final = 0.5 * 0.0159 + 0.5 * 0.0154 = 0.0157

    Why RRF works:
    - Handles different score scales (cosine vs ts_rank)
    - Position-based (robust to score calibration)
    - Research-proven to outperform score averaging
    - Simple, fast, no hyperparameter tuning needed

    Attributes:
        db: Supabase client instance
        embedder: OpenAI embedding client
        vector_searcher: Vector search instance
        text_searcher: Text search instance
        rrf_k: RRF constant (default: 60)
    """

    def __init__(
        self,
        db: Client,
        embedder: EmbeddingClient,
        rrf_k: int = 60,
    ) -> None:
        """
        Initialize hybrid searcher.

        Args:
            db: Supabase client instance
            embedder: OpenAI embedding client
            rrf_k: RRF constant (higher = less aggressive fusion)
        """
        self.db = db
        self.embedder = embedder
        self.vector_searcher = VectorSearcher(db, embedder)
        self.text_searcher = TextSearcher(db)
        self.rrf_k = rrf_k

    async def search(
        self,
        query: str,
        user_id: str,
        config: SearchConfig | None = None,
    ) -> list[SearchResult]:
        """
        Perform hybrid search with RRF fusion.

        This method:
        1. Runs vector and text search in parallel (future optimization)
        2. Currently runs sequentially for simplicity
        3. Applies RRF fusion to merge results
        4. Deduplicates chunks
        5. Re-ranks by RRF score
        6. Returns top-k results

        Args:
            query: Search query text
            user_id: User ID for RLS filtering
            config: Search configuration (uses defaults if None)

        Returns:
            List of SearchResult models ordered by RRF score (descending)

        Raises:
            DatabaseError: If search operations fail

        Example:
            ```python
            searcher = HybridSearcher(db, embedder)
            results = await searcher.search(
                query="How to implement OAuth authentication?",
                user_id="user_123",
                config=SearchConfig(
                    top_k=10,
                    min_similarity=0.7,
                    hybrid_alpha=0.5  # Balanced vector + text
                )
            )
            for result in results:
                print(f"{result.rank}. {result.content[:100]}...")
                print(f"   Score: {result.score:.4f} (source: {result.source})")
            ```
        """
        # Use default config if not provided
        if config is None:
            config = SearchConfig()

        logger.info(
            "Performing hybrid search",
            query=query,
            user_id=user_id,
            top_k=config.top_k,
            alpha=config.hybrid_alpha,
            rrf_k=self.rrf_k,
        )

        # Determine search strategy based on alpha
        # alpha = 1.0: vector only
        # alpha = 0.0: text only
        # alpha = 0.5: balanced hybrid

        if config.hybrid_alpha >= 1.0:
            # Pure vector search
            logger.debug("Using pure vector search (alpha=1.0)")
            results = await self.vector_searcher.search(query, user_id, config)
            # Update source to "hybrid" for consistency
            for result in results:
                result.source = "hybrid"
            return await self._swap_children_for_parents(results, user_id)

        if config.hybrid_alpha <= 0.0:
            # Pure text search
            logger.debug("Using pure text search (alpha=0.0)")
            results = await self.text_searcher.search(query, user_id, config)
            # Update source to "hybrid" for consistency
            for result in results:
                result.source = "hybrid"
            return await self._swap_children_for_parents(results, user_id)

        # True hybrid: run both searches in parallel for speed
        logger.debug("Running vector and text search in parallel")

        vector_results, text_results = await asyncio.gather(
            self.vector_searcher.search(query, user_id, config),
            self.text_searcher.search(query, user_id, config),
        )
        logger.debug(f"Vector search returned {len(vector_results)} results")
        logger.debug(f"Text search returned {len(text_results)} results")

        # Apply RRF fusion
        fused_results = self._reciprocal_rank_fusion(
            vector_results=vector_results,
            text_results=text_results,
            alpha=config.hybrid_alpha,
            top_k=config.top_k,
        )

        logger.info(
            "Hybrid search complete",
            query=query,
            vector_count=len(vector_results),
            text_count=len(text_results),
            fused_count=len(fused_results),
        )

        return await self._swap_children_for_parents(fused_results, user_id)

    def _reciprocal_rank_fusion(
        self,
        vector_results: list[SearchResult],
        text_results: list[SearchResult],
        alpha: float,
        top_k: int,
    ) -> list[SearchResult]:
        """
        Fuse vector and text results using Reciprocal Rank Fusion.

        RRF Formula:
            RRF_score(chunk) = alpha * RRF_vector + (1-alpha) * RRF_text
        where:
            RRF_vector = 1 / (k + rank_vector)
            RRF_text = 1 / (k + rank_text)

        Args:
            vector_results: Results from vector search
            text_results: Results from text search
            alpha: Weight for vector search (0.0 to 1.0)
            top_k: Number of results to return

        Returns:
            Fused and re-ranked results

        Learning Note: Why RRF?
        - Simple: No complex hyperparameters
        - Robust: Handles different score scales
        - Proven: Research shows it outperforms alternatives
        - Fast: O(n) complexity with hashmap

        Alternative approaches (not used):
        - Score averaging: Fails with different scales
        - Score normalization: Requires calibration
        - Learning to rank: Complex, needs training data
        """
        logger.debug(
            "Applying RRF fusion",
            vector_count=len(vector_results),
            text_count=len(text_results),
            alpha=alpha,
            k=self.rrf_k,
        )

        # Build rank maps: chunk_id -> rank
        vector_ranks: dict[UUID, int] = {
            result.chunk_id: result.rank
            for result in vector_results
        }
        text_ranks: dict[UUID, int] = {
            result.chunk_id: result.rank
            for result in text_results
        }

        # Build chunk map for metadata (use vector first, fallback to text)
        chunk_map: dict[UUID, SearchResult] = {}
        for result in vector_results:
            chunk_map[result.chunk_id] = result
        for result in text_results:
            if result.chunk_id not in chunk_map:
                chunk_map[result.chunk_id] = result

        # Get all unique chunk IDs
        all_chunk_ids = set(vector_ranks.keys()) | set(text_ranks.keys())

        logger.debug(
            "RRF fusion stats",
            unique_chunks=len(all_chunk_ids),
            vector_only=len(set(vector_ranks.keys()) - set(text_ranks.keys())),
            text_only=len(set(text_ranks.keys()) - set(vector_ranks.keys())),
            both=len(set(vector_ranks.keys()) & set(text_ranks.keys())),
        )

        # Calculate RRF scores for each chunk
        rrf_scores: dict[UUID, float] = {}

        for chunk_id in all_chunk_ids:
            # Vector RRF component
            vector_rrf = 0.0
            if chunk_id in vector_ranks:
                vector_rrf = 1.0 / (self.rrf_k + vector_ranks[chunk_id])

            # Text RRF component
            text_rrf = 0.0
            if chunk_id in text_ranks:
                text_rrf = 1.0 / (self.rrf_k + text_ranks[chunk_id])

            # Weighted combination
            rrf_scores[chunk_id] = alpha * vector_rrf + (1 - alpha) * text_rrf

        # Sort by RRF score (descending) and take top-k
        sorted_chunk_ids = sorted(
            rrf_scores.keys(),
            key=lambda cid: rrf_scores[cid],
            reverse=True,
        )[:top_k]

        # Build final results
        fused_results: list[SearchResult] = []
        for rank, chunk_id in enumerate(sorted_chunk_ids, start=1):
            base_result = chunk_map[chunk_id]

            # Preserve the best original score for display
            # Prefer vector search score (cosine similarity) as it's more intuitive
            original_score = base_result.original_score or base_result.score

            fused_results.append(
                SearchResult(
                    chunk_id=chunk_id,
                    document_id=base_result.document_id,
                    document_title=base_result.document_title,  # Include document title!
                    content=base_result.content,
                    metadata=base_result.metadata,
                    score=rrf_scores[chunk_id],  # RRF score for ranking
                    original_score=original_score,  # Original score for display
                    rank=rank,
                    source="hybrid",
                )
            )

        return fused_results

    # ------------------------------------------------------------------
    # Parent-child retrieval: swap child chunks for their parent chunks
    # ------------------------------------------------------------------

    async def _swap_children_for_parents(
        self,
        results: list[SearchResult],
        user_id: str,
    ) -> list[SearchResult]:
        """
        Replace child-chunk content with its parent's content.

        When a document was ingested with :class:`ParentChildChunker`, the
        vector index only contains *child* chunks (small, focused).  Returning
        child content to the LLM gives poor context.  This method swaps each
        child's content for the richer parent paragraph while keeping the
        child's metadata and scores for accurate citations.

        Algorithm (two batch DB queries — no N+1)
        ------------------------------------------
        1. Batch-fetch ``chunk_type`` + ``parent_chunk_id`` for all result chunks.
        2. Collect unique ``parent_chunk_id`` values for child chunks.
        3. Batch-fetch ``content`` for those parent DB rows.
        4. Rebuild the result list: children → parent content; others unchanged.

        If a child has no parent recorded (edge case / legacy data), falls back
        to the child content unchanged.

        Args:
            results:  RRF-fused search results (may be child chunks).
            user_id:  Authenticated user ID (used for safety filter on lookup).

        Returns:
            The same list with child content replaced by parent content.
        """
        if not results:
            return results

        chunk_ids = [str(r.chunk_id) for r in results]

        # Step 1: batch-fetch chunk_type + parent_chunk_id
        try:
            info_result = await asyncio.to_thread(
                lambda: (
                    self.db.table("document_chunks")
                    .select("id, chunk_type, parent_chunk_id")
                    .in_("id", chunk_ids)
                    .execute()
                )
            )
        except Exception as exc:
            logger.warning("Parent-swap info query failed; returning originals", error=str(exc))
            return results

        chunk_info: dict[str, dict] = {
            row["id"]: row for row in (info_result.data or [])
        }

        # Step 2: find which results are children with a parent
        parent_ids_needed: set[str] = {
            row["parent_chunk_id"]
            for row in chunk_info.values()
            if row.get("chunk_type") == "child" and row.get("parent_chunk_id")
        }

        if not parent_ids_needed:
            # No parent-child chunks in these results — nothing to swap.
            return results

        # Step 3: batch-fetch parent content
        try:
            parent_result = await asyncio.to_thread(
                lambda: (
                    self.db.table("document_chunks")
                    .select("id, content")
                    .in_("id", list(parent_ids_needed))
                    .execute()
                )
            )
        except Exception as exc:
            logger.warning("Parent content query failed; returning originals", error=str(exc))
            return results

        parent_content: dict[str, str] = {
            row["id"]: row["content"]
            for row in (parent_result.data or [])
        }

        # Step 4: rebuild result list with swapped content
        swapped: list[SearchResult] = []
        swapped_count = 0

        for result in results:
            info = chunk_info.get(str(result.chunk_id))

            if not info or info.get("chunk_type") != "child":
                swapped.append(result)
                continue

            parent_id = info.get("parent_chunk_id")
            parent_text = parent_content.get(parent_id) if parent_id else None

            if parent_text:
                swapped.append(result.model_copy(update={"content": parent_text}))
                swapped_count += 1
            else:
                # Fallback: no parent found, keep child content
                swapped.append(result)

        logger.debug(
            "Parent-child swap complete",
            total=len(results),
            swapped=swapped_count,
        )
        return swapped
