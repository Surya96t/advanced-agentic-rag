#!/usr/bin/env python3
"""
Test script to verify SQL functions are working correctly with document_title
"""
import structlog
from app.database.client import SupabaseClient
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


logger = structlog.get_logger()


def test_text_search():
    """Test the search_chunks_by_text function"""
    logger.info("Testing search_chunks_by_text function...")

    supabase = SupabaseClient.get_client()

    try:
        result = supabase.rpc('search_chunks_by_text', {
            'query_text': 'test',
            'match_count': 3,
            'filter_user_id': None,
            'ranking_function': 'ts_rank_cd'
        }).execute()

        logger.info(f"✅ Function callable", result_count=len(
            result.data) if result.data else 0)

        if result.data and len(result.data) > 0:
            sample = result.data[0]
            logger.info(f"Sample result columns: {list(sample.keys())}")

            if 'document_title' in sample:
                logger.info("✅ document_title column present")
                logger.info(
                    f"Sample document_title: {sample.get('document_title')}")
            else:
                logger.error("❌ document_title column MISSING!")

            if 'id' in sample:
                logger.info("✅ id column present")
            if 'content' in sample:
                logger.info("✅ content column present")
            if 'rank' in sample:
                logger.info("✅ rank column present")

        else:
            logger.warning("ℹ️  No results returned (database may be empty)")

    except Exception as e:
        logger.error(f"❌ Error testing text search: {e}")
        raise


def test_vector_search():
    """Test the search_chunks_by_embedding function"""
    logger.info("Testing search_chunks_by_embedding function...")

    supabase = SupabaseClient.get_client()

    try:
        # Create a dummy embedding vector (1536 dimensions for OpenAI)
        dummy_embedding = [0.0] * 1536

        result = supabase.rpc('search_chunks_by_embedding', {
            'query_embedding': dummy_embedding,
            'match_count': 3,
            'filter_user_id': None
        }).execute()

        logger.info(f"✅ Function callable", result_count=len(
            result.data) if result.data else 0)

        if result.data and len(result.data) > 0:
            sample = result.data[0]
            logger.info(f"Sample result columns: {list(sample.keys())}")

            if 'document_title' in sample:
                logger.info("✅ document_title column present")
                logger.info(
                    f"Sample document_title: {sample.get('document_title')}")
            else:
                logger.error("❌ document_title column MISSING!")

        else:
            logger.warning("ℹ️  No results returned (database may be empty)")

    except Exception as e:
        logger.error(f"❌ Error testing vector search: {e}")
        raise


def check_data_exists():
    """Check if there's any data in the database"""
    logger.info("Checking for data in document_chunks...")

    supabase = SupabaseClient.get_client()

    try:
        result = supabase.from_('document_chunks').select(
            'id, document_id, content').limit(1).execute()

        if result.data and len(result.data) > 0:
            logger.info(f"✅ Data exists in document_chunks table")

            # Check documents table for document_title
            doc_id = result.data[0]['document_id']
            doc_result = supabase.from_('documents').select(
                'id, title').eq('id', doc_id).execute()

            if doc_result.data and len(doc_result.data) > 0:
                doc_title = doc_result.data[0].get('title')
                logger.info(f"✅ Sample document title: '{doc_title}'")
            else:
                logger.warning(
                    "⚠️  No matching document found in documents table")

        else:
            logger.warning(
                "❌ No data found in document_chunks table - upload some documents first!")

    except Exception as e:
        logger.error(f"Error checking data: {e}")
        raise


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Testing SQL Functions for Citation Support")
    print("="*60 + "\n")

    check_data_exists()
    print("\n" + "-"*60 + "\n")
    test_text_search()
    print("\n" + "-"*60 + "\n")
    test_vector_search()
    print("\n" + "="*60)
    print("Test Complete!")
    print("="*60 + "\n")
