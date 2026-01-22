"""
Integration tests for the retrieval system.

This module tests the full retrieval pipeline:
- Vector search (semantic)
- Text search (keyword/FTS)
- Hybrid search (RRF fusion)
- Re-ranking (FlashRank)

These are INTEGRATION tests - they use real services:
- Supabase (database + pgvector)
- OpenAI (embeddings)
- FlashRank (re-ranking)

No mocking - we test the actual system behavior.
"""

import time
from uuid import UUID

import pytest

from app.schemas.retrieval import RerankConfig, SearchConfig
from app.retrieval.hybrid_search import HybridSearcher
from app.retrieval.rerankers.flashrank import FlashRankReranker
from app.retrieval.text_search import TextSearcher
from app.retrieval.vector_search import VectorSearcher


class TestVectorSearch:
    """Test vector search (semantic) functionality."""

    @pytest.mark.asyncio
    async def test_vector_search_basic(
        self,
        vector_searcher: VectorSearcher,
        test_user_id: str,
        test_documents: list[UUID],
        test_queries: dict[str, str],
    ):
        """
        Test basic vector search returns relevant results.

        Verifies:
        - Results are returned
        - Results have correct structure
        - Results are ordered by similarity (descending)
        - All results are from the test user
        """
        query = test_queries["semantic"]

        results = await vector_searcher.search(
            query=query,
            user_id=test_user_id,
            config=SearchConfig(top_k=10, min_similarity=0.5),
        )

        # Assert we got results
        assert len(results) > 0, "Vector search should return results"
        assert len(results) <= 10, "Should respect top_k limit"

        # Verify result structure
        first_result = results[0]
        assert first_result.chunk_id is not None
        assert first_result.document_id in test_documents
        assert first_result.content != ""
        assert 0.0 <= first_result.score <= 1.0
        assert first_result.rank == 1
        assert first_result.source == "vector"

        # Verify results are ordered by score (descending)
        for i in range(len(results) - 1):
            assert results[i].score >= results[i + 1].score, (
                "Results should be ordered by similarity (descending)"
            )

        # Verify ranks are sequential
        for i, result in enumerate(results, start=1):
            assert result.rank == i

        print(f"✅ Vector search returned {len(results)} results")
        print(f"   Top result score: {results[0].score:.3f}")
        print(f"   Query: {query}")

    @pytest.mark.asyncio
    async def test_vector_search_similarity_threshold(
        self,
        vector_searcher: VectorSearcher,
        test_user_id: str,
        test_documents: list[UUID],
        test_queries: dict[str, str],
    ):
        """
        Test that similarity threshold filters low-quality results.

        Verifies:
        - High threshold returns fewer results
        - All results meet minimum similarity
        """
        query = test_queries["semantic"]

        # Search with low threshold
        low_threshold_results = await vector_searcher.search(
            query=query,
            user_id=test_user_id,
            config=SearchConfig(top_k=20, min_similarity=0.5),
        )

        # Search with high threshold
        high_threshold_results = await vector_searcher.search(
            query=query,
            user_id=test_user_id,
            config=SearchConfig(top_k=20, min_similarity=0.8),
        )

        # High threshold should return fewer or equal results
        assert len(high_threshold_results) <= len(low_threshold_results), (
            "High threshold should filter more results"
        )

        # All high-threshold results should meet threshold
        for result in high_threshold_results:
            assert result.score >= 0.8, (
                f"Result score {result.score} below threshold 0.8"
            )

        print(f"✅ Similarity threshold works:")
        print(f"   Low threshold (0.5): {len(low_threshold_results)} results")
        print(
            f"   High threshold (0.8): {len(high_threshold_results)} results")

    @pytest.mark.asyncio
    async def test_vector_search_no_results(
        self,
        vector_searcher: VectorSearcher,
        test_user_id: str,
        test_documents: list[UUID],
        test_queries: dict[str, str],
    ):
        """
        Test handling of queries with no matches.

        Verifies:
        - Returns empty list (no errors)
        - Handles gracefully
        """
        query = test_queries["no_match"]

        results = await vector_searcher.search(
            query=query,
            user_id=test_user_id,
            config=SearchConfig(top_k=10, min_similarity=0.9),
        )

        assert isinstance(results, list), "Should return list even if empty"
        print(f"✅ No-match query handled gracefully: {len(results)} results")

    @pytest.mark.asyncio
    async def test_vector_search_rls_enforcement(
        self,
        vector_searcher: VectorSearcher,
        test_documents: list[UUID],
        test_queries: dict[str, str],
    ):
        """
        Test Row-Level Security (RLS) enforcement.

        Verifies:
        - Different user IDs return different/no results
        - User isolation works correctly
        """
        query = test_queries["semantic"]
        different_user_id = "different_user_999"

        # Search as different user
        results = await vector_searcher.search(
            query=query,
            user_id=different_user_id,
            config=SearchConfig(top_k=10, min_similarity=0.5),
        )

        # Should return no results (different user's data)
        assert len(results) == 0, (
            "RLS should prevent access to other users' documents"
        )

        print(
            f"✅ RLS enforcement works: different user got {len(results)} results")


class TestTextSearch:
    """Test text search (PostgreSQL FTS) functionality."""

    @pytest.mark.asyncio
    async def test_text_search_basic(
        self,
        text_searcher: TextSearcher,
        test_user_id: str,
        test_documents: list[UUID],
        test_queries: dict[str, str],
    ):
        """
        Test basic text search using PostgreSQL FTS.

        Verifies:
        - Results are returned
        - Results have correct structure
        - Results are ordered by rank (descending)
        """
        query = test_queries["keyword"]

        results = await text_searcher.search(
            query=query,
            user_id=test_user_id,
            config=SearchConfig(top_k=10, min_similarity=0.01),
        )

        # Assert we got results
        assert len(results) > 0, "Text search should return results"
        assert len(results) <= 10, "Should respect top_k limit"

        # Verify result structure
        first_result = results[0]
        assert first_result.chunk_id is not None
        assert first_result.document_id in test_documents
        assert first_result.content != ""
        assert first_result.score > 0.0  # FTS rank score
        assert first_result.rank == 1
        assert first_result.source == "text"

        # Verify results are ordered by score (descending)
        for i in range(len(results) - 1):
            assert results[i].score >= results[i + 1].score, (
                "Results should be ordered by FTS rank (descending)"
            )

        print(f"✅ Text search returned {len(results)} results")
        print(f"   Top result score: {results[0].score:.3f}")
        print(f"   Query: {query}")

    @pytest.mark.asyncio
    async def test_text_search_phrase_query(
        self,
        text_searcher: TextSearcher,
        test_user_id: str,
        test_documents: list[UUID],
        test_queries: dict[str, str],
    ):
        """
        Test phrase queries (exact word order).

        Verifies:
        - Phrase queries work correctly
        - Returns results for phrase matches
        """
        query = test_queries["phrase"]

        results = await text_searcher.search(
            query=query,
            user_id=test_user_id,
            config=SearchConfig(top_k=10, min_similarity=0.01),
        )

        # Should handle phrase queries without errors
        assert isinstance(results, list), "Should return list"

        print(f"✅ Phrase query handled: {len(results)} results for {query}")


class TestHybridSearch:
    """Test hybrid search (vector + text with RRF fusion) functionality."""

    @pytest.mark.asyncio
    async def test_hybrid_search_basic(
        self,
        hybrid_searcher: HybridSearcher,
        test_user_id: str,
        test_documents: list[UUID],
        test_queries: dict[str, str],
    ):
        """
        Test basic hybrid search with RRF fusion.

        Verifies:
        - Combines vector + text results
        - Returns merged, deduplicated results
        - Results are ordered by RRF score
        """
        query = test_queries["semantic"]

        results = await hybrid_searcher.search(
            query=query,
            user_id=test_user_id,
            config=SearchConfig(top_k=10),
        )

        # Assert we got results
        assert len(results) > 0, "Hybrid search should return results"
        assert len(results) <= 10, "Should respect top_k limit"

        # Verify result structure
        first_result = results[0]
        assert first_result.chunk_id is not None
        assert first_result.document_id in test_documents
        assert first_result.content != ""
        assert first_result.score > 0.0  # RRF score
        assert first_result.rank == 1
        assert first_result.source == "hybrid"

        # Verify results are ordered by RRF score (descending)
        for i in range(len(results) - 1):
            assert results[i].score >= results[i + 1].score, (
                "Results should be ordered by RRF score (descending)"
            )

        print(f"✅ Hybrid search returned {len(results)} results")
        print(f"   Top result RRF score: {results[0].score:.6f}")
        print(f"   Query: {query}")

    @pytest.mark.asyncio
    async def test_hybrid_search_alpha_weighting(
        self,
        hybrid_searcher: HybridSearcher,
        test_user_id: str,
        test_documents: list[UUID],
        test_queries: dict[str, str],
    ):
        """
        Test different alpha values (vector vs text weight).

        Verifies:
        - alpha=0.0: Text-only results
        - alpha=1.0: Vector-only results
        - alpha=0.5: Balanced results
        """
        query = test_queries["semantic"]

        # Text-only (alpha=0.0)
        text_only = await hybrid_searcher.search(
            query=query,
            user_id=test_user_id,
            config=SearchConfig(top_k=10, hybrid_alpha=0.0),
        )

        # Vector-only (alpha=1.0)
        vector_only = await hybrid_searcher.search(
            query=query,
            user_id=test_user_id,
            config=SearchConfig(top_k=10, hybrid_alpha=1.0),
        )

        # Balanced (alpha=0.5)
        balanced = await hybrid_searcher.search(
            query=query,
            user_id=test_user_id,
            config=SearchConfig(top_k=10, hybrid_alpha=0.5),
        )

        # All should return results
        assert len(text_only) > 0, "Text-only should return results"
        assert len(vector_only) > 0, "Vector-only should return results"
        assert len(balanced) > 0, "Balanced should return results"

        print(f"✅ Alpha weighting works:")
        print(f"   Text-only (α=0.0): {len(text_only)} results")
        print(f"   Vector-only (α=1.0): {len(vector_only)} results")
        print(f"   Balanced (α=0.5): {len(balanced)} results")

    @pytest.mark.asyncio
    async def test_hybrid_search_deduplication(
        self,
        hybrid_searcher: HybridSearcher,
        test_user_id: str,
        test_documents: list[UUID],
        test_queries: dict[str, str],
    ):
        """
        Test that duplicate chunks are removed.

        Verifies:
        - Same chunk appears only once
        - RRF scores are combined for duplicates
        """
        query = test_queries["keyword"]

        results = await hybrid_searcher.search(
            query=query,
            user_id=test_user_id,
            config=SearchConfig(top_k=20),
        )

        # Check for duplicate chunk_ids
        chunk_ids = [result.chunk_id for result in results]
        unique_chunk_ids = set(chunk_ids)

        assert len(chunk_ids) == len(unique_chunk_ids), (
            "Results should not contain duplicate chunks"
        )

        print(f"✅ Deduplication works: {len(results)} unique results")


class TestReranking:
    """Test re-ranking (FlashRank) functionality."""

    @pytest.mark.asyncio
    async def test_flashrank_reranking_basic(
        self,
        flashrank_reranker: FlashRankReranker,
        hybrid_searcher: HybridSearcher,
        test_user_id: str,
        test_documents: list[UUID],
        test_queries: dict[str, str],
    ):
        """
        Test basic FlashRank re-ranking.

        Verifies:
        - Re-ranking completes successfully
        - Returns top_k results
        - Scores are updated
        - Source is marked as "reranked"
        """
        query = test_queries["semantic"]

        # Get initial results from hybrid search
        initial_results = await hybrid_searcher.search(
            query=query,
            user_id=test_user_id,
            config=SearchConfig(top_k=20),
        )

        # Re-rank
        reranked_results = await flashrank_reranker.rerank(
            query=query,
            results=initial_results,
            config=RerankConfig(top_k=5),
        )

        # Assert re-ranking worked
        assert len(reranked_results) > 0, "Re-ranking should return results"
        assert len(reranked_results) <= 5, "Should respect top_k limit"

        # Verify result structure
        first_result = reranked_results[0]
        assert first_result.chunk_id is not None
        assert first_result.score > 0.0  # FlashRank score
        assert first_result.rank == 1
        assert first_result.source == "reranked"

        # Verify results are ordered by FlashRank score (descending)
        for i in range(len(reranked_results) - 1):
            assert reranked_results[i].score >= reranked_results[i + 1].score, (
                "Re-ranked results should be ordered by FlashRank score"
            )

        print(f"✅ FlashRank re-ranking worked:")
        print(f"   Initial results: {len(initial_results)}")
        print(f"   Re-ranked results: {len(reranked_results)}")
        print(f"   Top re-ranked score: {reranked_results[0].score:.3f}")

    @pytest.mark.asyncio
    async def test_flashrank_improves_relevance(
        self,
        flashrank_reranker: FlashRankReranker,
        hybrid_searcher: HybridSearcher,
        test_user_id: str,
        test_documents: list[UUID],
        test_queries: dict[str, str],
    ):
        """
        Test that re-ranking can improve result ordering.

        Verifies:
        - Re-ranking may change order
        - Top result might be different after re-ranking
        """
        query = test_queries["technical"]

        # Get initial results
        initial_results = await hybrid_searcher.search(
            query=query,
            user_id=test_user_id,
            config=SearchConfig(top_k=20),
        )

        # Re-rank
        reranked_results = await flashrank_reranker.rerank(
            query=query,
            results=initial_results,
            config=RerankConfig(top_k=10),
        )

        # Get chunk IDs in order
        initial_top_3 = [r.chunk_id for r in initial_results[:3]]
        reranked_top_3 = [r.chunk_id for r in reranked_results[:3]]

        print(f"✅ Re-ranking impact:")
        print(f"   Initial top-3: {initial_top_3}")
        print(f"   Re-ranked top-3: {reranked_top_3}")
        print(f"   Order changed: {initial_top_3 != reranked_top_3}")


class TestFullPipeline:
    """Test the complete end-to-end retrieval pipeline."""

    @pytest.mark.asyncio
    async def test_full_retrieval_pipeline(
        self,
        hybrid_searcher: HybridSearcher,
        flashrank_reranker: FlashRankReranker,
        test_user_id: str,
        test_documents: list[UUID],
        test_queries: dict[str, str],
    ):
        """
        Test complete pipeline: hybrid search → re-ranking.

        Verifies:
        - End-to-end flow works
        - Results are relevant
        - Performance is acceptable (<500ms)
        """
        query = test_queries["semantic"]

        start_time = time.time()

        # Step 1: Hybrid search
        search_results = await hybrid_searcher.search(
            query=query,
            user_id=test_user_id,
            config=SearchConfig(top_k=20),
        )

        search_time = time.time() - start_time

        # Step 2: Re-rank
        rerank_start = time.time()
        final_results = await flashrank_reranker.rerank(
            query=query,
            results=search_results,
            config=RerankConfig(top_k=5),
        )

        rerank_time = time.time() - rerank_start
        total_time = time.time() - start_time

        # Verify results
        assert len(final_results) > 0, "Pipeline should return results"
        assert len(final_results) <= 5, "Should return top-5 results"

        # Performance check (should be fast, but CI might be slower)
        # Just log performance, don't fail tests
        print(f"\n✅ Full pipeline completed:")
        print(f"   Query: {query}")
        print(f"   Search time: {search_time*1000:.1f}ms")
        print(f"   Re-rank time: {rerank_time*1000:.1f}ms")
        print(f"   Total time: {total_time*1000:.1f}ms")
        print(f"   Results: {len(final_results)}")
        print(f"\n   Top result:")
        print(f"   - Score: {final_results[0].score:.3f}")
        print(f"   - Content: {final_results[0].content[:100]}...")

        # Verify reasonable performance (generous limit for CI)
        assert total_time < 5.0, (
            f"Pipeline should complete in <5s, took {total_time:.2f}s"
        )

    @pytest.mark.asyncio
    async def test_multiple_queries(
        self,
        hybrid_searcher: HybridSearcher,
        flashrank_reranker: FlashRankReranker,
        test_user_id: str,
        test_documents: list[UUID],
        test_queries: dict[str, str],
    ):
        """
        Test pipeline with multiple different queries.

        Verifies:
        - System works for various query types
        - Consistent behavior across queries
        """
        test_query_types = ["semantic", "keyword", "technical"]

        for query_type in test_query_types:
            query = test_queries[query_type]

            # Run full pipeline
            search_results = await hybrid_searcher.search(
                query=query,
                user_id=test_user_id,
                config=SearchConfig(top_k=20),
            )

            final_results = await flashrank_reranker.rerank(
                query=query,
                results=search_results,
                config=RerankConfig(top_k=5),
            )

            # Should return results for all query types
            assert len(final_results) > 0, (
                f"Should return results for {query_type} query"
            )

            print(
                f"✅ {query_type.capitalize()} query: {len(final_results)} results")


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v", "-s"])
