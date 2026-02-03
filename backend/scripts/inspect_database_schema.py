#!/usr/bin/env python3
"""
Inspect the actual database schema to understand column names and structure.
"""
import structlog
from app.database.client import SupabaseClient
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


logger = structlog.get_logger()


def inspect_schema():
    """Inspect database schema and actual data"""
    logger.info("Inspecting database schema...")

    supabase = SupabaseClient.get_client()

    print("\n" + "="*80)
    print("DATABASE SCHEMA INSPECTION")
    print("="*80 + "\n")

    # 1. Check document_chunks table structure
    print("1. DOCUMENT_CHUNKS TABLE STRUCTURE")
    print("-" * 80)

    try:
        # Get a sample row to see all columns
        result = supabase.from_('document_chunks').select(
            '*').limit(1).execute()

        if result.data and len(result.data) > 0:
            sample = result.data[0]
            print(f"✅ Columns in document_chunks table:")
            for col_name in sorted(sample.keys()):
                value = sample[col_name]
                value_type = type(value).__name__
                value_preview = str(value)[:50] if value else "NULL"
                print(f"   - {col_name:20} ({value_type:15}): {value_preview}")
        else:
            print("⚠️  No data in document_chunks table")

    except Exception as e:
        print(f"❌ Error inspecting document_chunks: {e}")

    print("\n" + "-" * 80 + "\n")

    # 2. Check documents table structure
    print("2. DOCUMENTS TABLE STRUCTURE")
    print("-" * 80)

    try:
        result = supabase.from_('documents').select('*').limit(1).execute()

        if result.data and len(result.data) > 0:
            sample = result.data[0]
            print(f"✅ Columns in documents table:")
            for col_name in sorted(sample.keys()):
                value = sample[col_name]
                value_type = type(value).__name__
                value_preview = str(value)[:50] if value else "NULL"
                print(f"   - {col_name:20} ({value_type:15}): {value_preview}")
        else:
            print("⚠️  No data in documents table")

    except Exception as e:
        print(f"❌ Error inspecting documents: {e}")

    print("\n" + "-" * 80 + "\n")

    # 3. Check what the SQL function actually returns
    print("3. SQL FUNCTION OUTPUT (search_chunks_by_text)")
    print("-" * 80)

    try:
        result = supabase.rpc('search_chunks_by_text', {
            'query_text': 'test',
            'match_count': 1,
            'filter_user_id': None,
            'ranking_function': 'ts_rank_cd'
        }).execute()

        if result.data and len(result.data) > 0:
            sample = result.data[0]
            print(f"✅ Columns returned by search_chunks_by_text:")
            for col_name in sorted(sample.keys()):
                value = sample[col_name]
                value_type = type(value).__name__
                value_preview = str(value)[:50] if value else "NULL"
                print(f"   - {col_name:20} ({value_type:15}): {value_preview}")
        else:
            print("⚠️  No results from search_chunks_by_text")

    except Exception as e:
        print(f"❌ Error calling search_chunks_by_text: {e}")

    print("\n" + "-" * 80 + "\n")

    # 4. Check what the SQL function actually returns
    print("4. SQL FUNCTION OUTPUT (search_chunks_by_embedding)")
    print("-" * 80)

    try:
        dummy_embedding = [0.0] * 1536
        result = supabase.rpc('search_chunks_by_embedding', {
            'query_embedding': dummy_embedding,
            'match_count': 1,
            'filter_user_id': None
        }).execute()

        if result.data and len(result.data) > 0:
            sample = result.data[0]
            print(f"✅ Columns returned by search_chunks_by_embedding:")
            for col_name in sorted(sample.keys()):
                value = sample[col_name]
                value_type = type(value).__name__
                value_preview = str(value)[:50] if value else "NULL"
                print(f"   - {col_name:20} ({value_type:15}): {value_preview}")
        else:
            print("⚠️  No results from search_chunks_by_embedding")

    except Exception as e:
        print(f"❌ Error calling search_chunks_by_embedding: {e}")

    print("\n" + "="*80)
    print("INSPECTION COMPLETE")
    print("="*80 + "\n")


if __name__ == "__main__":
    inspect_schema()
