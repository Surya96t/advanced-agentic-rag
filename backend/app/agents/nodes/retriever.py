"""
Retrieval node for hybrid search and re-ranking.

This module executes multi-query hybrid search, deduplicates results,
and applies re-ranking for optimal chunk selection.
"""

from langgraph.types import RunnableConfig

from app.agents.state import AgentState
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
        # Using rank-T5-flan as it's more reliable than ms-marco-MiniLM-L-6-v2
        _reranker = FlashRankReranker(model_name="rank-T5-flan")
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
    logger.info("Retriever node: Starting multi-query hybrid search")

    # Extract user_id from config (provided by graph invoke/stream call)
    user_id = config.get("configurable", {}).get("user_id", "")

    # Fallback to test user if empty (for LangGraph Studio testing)
    # In production, this should come from authenticated context
    if not user_id or user_id == "anonymous":
        user_id = "test_user_integration_123"  # Default test user for dev/testing
        logger.warning(
            f"No user_id provided in config, using test user: {user_id}"
        )

    # Get queries to search
    # If expanded_queries exist, use them, otherwise use original_query
    queries = state.get("expanded_queries", [])
    if not queries:
        queries = [state["original_query"]]

    logger.info(f"Searching {len(queries)} queries for user {user_id}")

    # Initialize searcher and reranker
    searcher = get_hybrid_searcher()
    # TODO: Fix FlashRank model download issue
    # For now, we'll skip reranking and rely on hybrid search scores
    # reranker = get_reranker()
    reranker = None

    # Search configuration
    search_config = SearchConfig(
        top_k=10,  # Get 10 results per query
        min_similarity=0.0,  # No filtering (reranker will handle quality)
        hybrid_alpha=0.5,  # Balanced vector + text
    )

    # Step 1: Search each query
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

    if not all_results:
        logger.warning("No results found for any query")
        return {
            "retrieved_chunks": [],
            "sources": [],
            "metadata": {"retrieval": {"queries_searched": len(queries), "total_results": 0}}
        }

    logger.info(f"Total results from all queries: {len(all_results)}")

    # Step 2: Deduplicate by chunk_id (keep highest score)
    # Build dict of chunk_id -> SearchResult
    unique_results: dict[str, SearchResult] = {}
    for result in all_results:
        chunk_id = str(result.chunk_id)
        if chunk_id not in unique_results or result.score > unique_results[chunk_id].score:
            unique_results[chunk_id] = result

    deduplicated = list(unique_results.values())
    logger.info(f"After deduplication: {len(deduplicated)} unique chunks")

    # Step 3: Re-rank using FlashRank
    # Use original query for re-ranking (most representative)
    original_query = state["original_query"]

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

    # Step 4: Build sources for citation
    sources = [
        {
            "chunk_id": str(result.chunk_id),
            "document_id": str(result.document_id),
            "document_title": result.metadata.get("document_title", "Unknown"),
            "score": result.score,
            "source": result.source,
        }
        for result in reranked_results
    ]

    logger.info(
        "Retrieval complete",
        queries_searched=len(queries),
        total_found=len(all_results),
        after_dedup=len(deduplicated),
        final_count=len(reranked_results)
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
            }
        }
    }
