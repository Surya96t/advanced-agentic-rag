#!/usr/bin/env python3
"""
Performance testing script for Integration Forge.

This script runs a test query through the RAG pipeline and displays
detailed timing information for each node.

Usage:
    cd backend
    uv run python scripts/test_performance.py
"""

from app.utils.logger import get_logger
from app.agents.graph import get_graph
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


logger = get_logger(__name__)


async def run_performance_test():
    """Run a test query and measure performance."""

    print("\n" + "=" * 80)
    print("🚀 PERFORMANCE TEST - Integration Forge RAG Pipeline")
    print("=" * 80)
    print()

    # Get the compiled graph
    graph = await get_graph()

    # Test query (you can modify this)
    test_query = "How do I authenticate users with Clerk?"

    print(f"Test Query: {test_query}")
    print()
    print("=" * 80)
    print("Starting pipeline execution...")
    print("=" * 80)
    print()

    # Invoke the graph
    try:
        result = await graph.ainvoke(
            {
                "original_query": test_query,
                "messages": [],
                "retry_count": 0,
            },
            config={
                "configurable": {
                    "user_id": "test_user_integration_123",
                    "thread_id": "performance_test_thread",
                }
            }
        )

        print()
        print("=" * 80)
        print("✅ PIPELINE COMPLETE")
        print("=" * 80)
        print()

        # Display results summary
        print("📊 RESULTS SUMMARY:")
        print("-" * 80)
        print(f"Query Complexity: {result.get('query_complexity', 'N/A')}")
        print(f"Expanded Queries: {len(result.get('expanded_queries', []))}")
        print(f"Retrieved Chunks: {len(result.get('retrieved_chunks', []))}")
        print(
            f"Validation Score: {result.get('validation_result', {}).get('score', 'N/A')}")
        print(f"Retry Count: {result.get('retry_count', 0)}")
        print()

        # Display response preview
        response = result.get('generated_response', '')
        print("📝 RESPONSE PREVIEW:")
        print("-" * 80)
        print(response[:500] + "..." if len(response) > 500 else response)
        print()

        # Display metadata if available
        metadata = result.get('metadata', {})
        if 'generation' in metadata:
            gen_meta = metadata['generation']
            print("📈 GENERATION METRICS:")
            print("-" * 80)
            print(f"Model: {gen_meta.get('model', 'N/A')}")
            print(f"Prompt Tokens: {gen_meta.get('prompt_tokens', 'N/A')}")
            print(
                f"Completion Tokens: {gen_meta.get('completion_tokens', 'N/A')}")
            print(f"Total Tokens: {gen_meta.get('total_tokens', 'N/A')}")
            print(f"Latency: {gen_meta.get('latency_ms', 'N/A')}ms")
            print(
                f"Estimated Cost: ${gen_meta.get('estimated_cost_usd', 'N/A')}")
            print()

        if 'retrieval' in metadata:
            ret_meta = metadata['retrieval']
            print("🔍 RETRIEVAL METRICS:")
            print("-" * 80)
            print(
                f"Queries Searched: {ret_meta.get('queries_searched', 'N/A')}")
            print(
                f"Total Results Found: {ret_meta.get('total_results', 'N/A')}")
            print(f"After Deduplication: {ret_meta.get('after_dedup', 'N/A')}")
            print(f"Final Count: {ret_meta.get('reranked_count', 'N/A')}")
            print()

        print("=" * 80)
        print("💡 TIP: Check the logs above for detailed timing breakdowns!")
        print("=" * 80)
        print()

        return result

    except Exception as e:
        print()
        print("=" * 80)
        print("❌ ERROR DURING EXECUTION")
        print("=" * 80)
        print(f"Error: {str(e)}")
        print()
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    print("\n🔧 Initializing performance test...\n")
    result = asyncio.run(run_performance_test())

    if result:
        print("✅ Performance test completed successfully!")
        sys.exit(0)
    else:
        print("❌ Performance test failed!")
        sys.exit(1)
