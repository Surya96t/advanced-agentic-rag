"""
Retrieval node for hybrid search and re-ranking.

This module executes multi-query hybrid search, deduplicates results,
and applies re-ranking for optimal chunk selection.
"""

import time
from langgraph.types import RunnableConfig

from app.agents.state import AgentState
from app.core.config import settings
from app.database.client import SupabaseClient
from app.ingestion.embeddings import EmbeddingClient
from app.retrieval.hybrid_search import HybridSearcher
from app.retrieval.rerankers.flashrank import FlashRankReranker
from app.schemas.retrieval import RerankConfig, SearchConfig, SearchResult
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Initialize retrieval components (singletons)
_embedding_client: EmbeddingClient | None = None
_hybrid_searcher: HybridSearcher | None = None
_reranker: FlashRankReranker | None = None


def get_embedding_client() -> EmbeddingClient:
    """Get or create embedding client singleton."""
    global _embedding_client
    if _embedding_client is None:
        _embedding_client = EmbeddingClient()
    return _embedding_client


def get_hybrid_searcher() -> HybridSearcher:
    """Get or create hybrid searcher singleton."""
    global _hybrid_searcher
    if _hybrid_searcher is None:
        db = SupabaseClient.get_client()
        embedder = get_embedding_client()
        _hybrid_searcher = HybridSearcher(db=db, embedder=embedder)
    return _hybrid_searcher


def get_reranker() -> FlashRankReranker:
    """Get or create reranker singleton."""
    global _reranker
    if _reranker is None:
        # Using ms-marco-MiniLM-L-12-v2 for better score calibration (0-1 range)
        # rank-T5-flan tends to output raw logits or low probabilities (~0.4-0.5 for good matches)
        _reranker = FlashRankReranker(model_name="ms-marco-MiniLM-L-12-v2")
    return _reranker


async def retriever_node(state: AgentState, config: RunnableConfig) -> dict:
    """
    Retrieval node that executes multi-query hybrid search with re-ranking.

    Process:
    1. Get queries (expanded_queries or original_query)
    2. For each query, run hybrid search
    3. Aggregate and deduplicate results (handled by state reducer)
    4. Re-rank using FlashRank
    5. Keep top-5 results
    6. Return with metadata

    Args:
        state: Current agent state with queries
        config: LangGraph config (contains configurable params like user_id)

    Returns:
        State update dict with retrieved_chunks and sources

    Example:
        >>> state = {
        ...     "expanded_queries": ["How does Clerk work?", "Prisma setup?"],
        ...     "original_query": "integrate Clerk with Prisma"
        ... }
        >>> result = await retriever_node(state, {"configurable": {"user_id": "user_123"}})
        >>> len(result["retrieved_chunks"])
        5
    """
    start_time = time.time()
    logger.info("⏱️  RETRIEVER NODE: Starting multi-query hybrid search")

    # Extract user_id from config (provided by graph invoke/stream call)
    user_id = config.get("configurable", {}).get("user_id", "")

    # Validate user_id based on environment
    if not user_id or user_id == "anonymous":
        # SECURITY: In production, user_id is REQUIRED
        # Fail fast rather than using a fallback that could leak data
        if settings.environment == "production":
            logger.error(
                "user_id is required in production but was not provided")
            raise ValueError(
                "user_id is required for retrieval in production environment. "
                "Ensure authentication middleware is properly configured."
            )

        # Development/Testing: Allow fallback to test user
        # This enables LangGraph Studio and local testing
        user_id = "test_user_integration_123"
        logger.warning(
            f"No user_id provided in {settings.environment} environment, "
            f"using test user: {user_id}. "
            f"This is only allowed in non-production environments."
        )

    # Get queries to search
    # If expanded_queries exist, use them, otherwise use original_query
    queries = state.get("expanded_queries", [])
    if not queries:
        # Defensive: ensure original_query exists and is not empty
        original_query = state.get("original_query", "").strip()
        if not original_query:
            logger.error(
                "No queries available: both expanded_queries and original_query are missing or empty")
            raise ValueError(
                "Cannot perform retrieval: no query provided. "
                "State must contain either 'expanded_queries' or 'original_query'."
            )
        queries = [original_query]

    logger.info(f"Searching {len(queries)} queries for user {user_id}")

    # Initialize searcher and reranker
    searcher = get_hybrid_searcher()
    # Re-enable FlashRank for re-ranking to improve result quality
    try:
        reranker = get_reranker()
        logger.info("FlashRank reranker initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize FlashRank reranker: {e}")
        reranker = None

    # Search configuration
    search_config = SearchConfig(
        top_k=20,  # High recall for re-ranking candidate pool
        # Lower similarity threshold allowed because reranker will filter noise
        # 0.01 captures almost everything for re-ranking
        min_similarity=0.01,
        hybrid_alpha=0.5,  # Balanced vector + text
    )

    # Step 1: Search each query
    search_start = time.time()
    all_results: list[SearchResult] = []
    for idx, query in enumerate(queries, 1):
        logger.info(f"Searching query {idx}/{len(queries)}: {query[:100]}...")

        try:
            results = await searcher.search(
                query=query,
                user_id=user_id,
                config=search_config
            )

            logger.info(f"Query {idx} returned {len(results)} results")
            all_results.extend(results)

        except Exception as e:
            logger.error(f"Search failed for query {idx}: {e}")
            # Continue with other queries
            continue

    search_time = time.time() - search_start
    logger.info(f"  ↳ All searches completed in {search_time:.3f}s")

    if not all_results:
        elapsed_time = time.time() - start_time
        logger.warning(
            f"⏱️  RETRIEVER NODE: Completed in {elapsed_time:.3f}s | No results found")
        return {
            "retrieved_chunks": [],
            "sources": [],
            "metadata": {"retrieval": {"queries_searched": len(queries), "total_results": 0}}
        }

    logger.info(f"Total results from all queries: {len(all_results)}")

    # Step 2: Deduplicate by chunk_id (keep highest score)
    dedup_start = time.time()
    # Build dict of chunk_id -> SearchResult
    unique_results: dict[str, SearchResult] = {}
    for result in all_results:
        chunk_id = str(result.chunk_id)
        if chunk_id not in unique_results or result.score > unique_results[chunk_id].score:
            unique_results[chunk_id] = result

    deduplicated = list(unique_results.values())
    dedup_time = time.time() - dedup_start
    logger.info(
        f"  ↳ Deduplication took {dedup_time:.3f}s | {len(deduplicated)} unique chunks")

    # Step 3: Re-rank using FlashRank
    rerank_start = time.time()
    # Use original query for re-ranking (most representative)
    # Defensive: retrieve original_query safely (should always exist after validation above)
    original_query = state.get("original_query", "")
    if not original_query:
        # This shouldn't happen after validation above, but handle defensively
        logger.warning(
            "original_query missing during re-ranking, using first expanded query as fallback")
        original_query = queries[0] if queries else ""

    # Skip reranking if reranker is not available
    if reranker is None:
        logger.warning("Reranker not available, using hybrid search scores")
        reranked_results = sorted(
            deduplicated, key=lambda x: x.score, reverse=True)[:5]
    else:
        logger.info("Re-ranking results with FlashRank")
        rerank_config = RerankConfig(top_k=5)  # Keep top-5 after re-ranking

        try:
            reranked_results = await reranker.rerank(
                query=original_query,
                results=deduplicated,
                config=rerank_config
            )

            logger.info(
                f"Re-ranking complete: {len(reranked_results)} top results selected")

        except Exception as e:
            logger.error(f"Re-ranking failed: {e}, using hybrid scores")
            # Fallback: use hybrid search scores
            reranked_results = sorted(
                deduplicated, key=lambda x: x.score, reverse=True)[:5]

    rerank_time = time.time() - rerank_start
    logger.info(f"  ↳ Re-ranking took {rerank_time:.3f}s")

    # Step 4: Build sources for citation
    sources = [
        {
            "chunk_id": str(result.chunk_id),
            "document_id": str(result.document_id),
            # Use the actual document_title field, not metadata!
            "document_title": result.document_title,
            "score": result.score,  # RRF or reranked score
            # Original cosine similarity for display
            "original_score": result.original_score,
            "source": result.source,
        }
        for result in reranked_results
    ]

    elapsed_time = time.time() - start_time
    logger.info(
        f"⏱️  RETRIEVER NODE: Completed in {elapsed_time:.3f}s | "
        f"Queries: {len(queries)} | Results: {len(all_results)} → {len(deduplicated)} → {len(reranked_results)}"
    )

    # Return state updates
    # Note: retrieved_chunks uses add_search_results reducer (handles dedup)
    # sources uses add_sources reducer (handles dedup by document_id)
    return {
        "retrieved_chunks": reranked_results,
        "sources": sources,
        "metadata": {
            "retrieval": {
                "queries_searched": len(queries),
                "total_results": len(all_results),
                "after_dedup": len(deduplicated),
                "reranked_count": len(reranked_results),
                "timing": {
                    "search": f"{search_time:.3f}s",
                    "dedup": f"{dedup_time:.3f}s",
                    "rerank": f"{rerank_time:.3f}s",
                    "total": f"{elapsed_time:.3f}s"
                }
            }
        }
    }
