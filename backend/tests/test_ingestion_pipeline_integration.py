"""
Integration test for the complete ingestion pipeline.

This test validates the end-to-end flow:
1. Load a real document from data/raw/
2. Parse it with DocumentParser
3. Chunk it with RecursiveChunker
4. Generate embeddings with OpenAI
5. Store in Supabase
6. Verify the results

Requirements:
- Supabase instance running
- OpenAI API key configured
- Environment variables loaded

Learning Note:
Why an integration test?
- Unit tests mock dependencies (fast, isolated)
- Integration tests use real dependencies (slow, realistic)
- This tests the ENTIRE system end-to-end
- Catches issues that unit tests miss (API changes, DB schema, etc.)

To run:
```bash
pytest tests/test_ingestion_pipeline_integration.py -v -s
```

The -s flag shows print statements for debugging.
"""

import asyncio
from pathlib import Path
from uuid import uuid4

import pytest

from app.database.client import SupabaseClient
from app.database.repositories.chunks import ChunkRepository
from app.database.repositories.documents import DocumentRepository
from app.ingestion.embeddings import get_embedding_client
from app.ingestion.pipeline import IngestionPipeline


# ============================================================================
# TEST CONFIGURATION
# ============================================================================


# Path to test data (relative to backend/)
TEST_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "raw"
TEST_FILE = TEST_DATA_DIR / "convex" / "mutations.md"


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
async def pipeline():
    """
    Create ingestion pipeline with real dependencies.

    This fixture:
    - Uses real Supabase client
    - Uses real OpenAI embeddings
    - No mocks - full integration test
    """
    supabase = SupabaseClient.get_client()
    doc_repo = DocumentRepository(supabase)
    chunk_repo = ChunkRepository(supabase)
    embedding_client = await get_embedding_client()

    return IngestionPipeline(
        doc_repo=doc_repo,
        chunk_repo=chunk_repo,
        embedding_client=embedding_client,
    )


@pytest.fixture
def test_user_id():
    """
    Generate a test user ID and create user record.

    In production, this would come from Clerk JWT token.
    For testing, we create a user in the database with Clerk-style ID.
    
    NOTE: Uses service role key to bypass RLS.
    
    IMPORTANT: users.id is TEXT type for Clerk compatibility (e.g., "user_2bXYZ123").
    """
    # Generate Clerk-style user ID
    user_id = f"user_test_{uuid4().hex[:12]}"  # e.g., "user_test_a3b5c7d9e1f2"
    
    # Create user record in database
    supabase = SupabaseClient.get_client()
    try:
        # Insert with Clerk-style user ID
        result = supabase.table("users").insert({
            "id": user_id,  # TEXT field for Clerk user ID
            "email": f"test_{user_id}@example.com",
        }).execute()
        
        # Verify the user was actually created
        if not result.data or len(result.data) == 0:
            raise ValueError(f"User creation returned empty data: {result}")
        
        created_user = result.data[0]
        print(f"\n✅ Created test user:")
        print(f"   ID: {created_user['id']}")
        print(f"   Email: {created_user['email']}")
        
    except Exception as e:
        print(f"\n❌ Failed to create test user: {e}")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Error details: {str(e)}")
        print(f"   Attempted user_id: {user_id}")
        raise
    
    yield user_id
    
    # Cleanup after test
    try:
        delete_result = supabase.table("users").delete().eq("id", user_id).execute()
        print(f"\n🧹 Cleaned up test user: {user_id}")
        print(f"   Deleted rows: {len(delete_result.data) if delete_result.data else 0}")
    except Exception as e:
        print(f"\n⚠️  Failed to cleanup test user: {e}")


@pytest.fixture
def progress_tracker():
    """
    Progress callback that prints updates.

    Useful for debugging and seeing what's happening during ingestion.
    """
    def callback(state: dict) -> None:
        print(
            f"\n[PROGRESS] {state['stage']} ({state['percentage']:.1f}%) - {state['message']}")

    return callback


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_ingest_real_document(pipeline, test_user_id, progress_tracker):
    """
    Test ingesting a real document from data/raw/.

    This is the main integration test that validates:
    1. Document parsing works
    2. Chunking produces valid chunks
    3. Embeddings are generated
    4. Data is stored in Supabase
    5. Progress tracking works

    Expected outcome:
    - Document record created with status=COMPLETED
    - Multiple chunks created (depends on file size)
    - Each chunk has a valid embedding vector
    - Metadata preserved throughout pipeline
    """
    # Ensure test file exists
    assert TEST_FILE.exists(), f"Test file not found: {TEST_FILE}"

    # Read file content
    with open(TEST_FILE, "rb") as f:
        file_bytes = f.read()

    print(f"\n{'='*80}")
    print(f"INTEGRATION TEST: Ingesting {TEST_FILE.name}")
    print(f"File size: {len(file_bytes)} bytes")
    print(f"User ID: {test_user_id}")
    print(f"{'='*80}")

    # Ingest document
    document = await pipeline.ingest_document(
        file_bytes=file_bytes,
        filename=TEST_FILE.name,
        user_id=test_user_id,
        metadata={
            "source": "convex-docs",
            "category": "mutations",
            "test": True,  # Mark as test data for cleanup
        },
        progress_callback=progress_tracker,
    )

    # Validate document
    print(f"\n{'='*80}")
    print(f"DOCUMENT CREATED:")
    print(f"  ID: {document.id}")
    print(f"  Title: {document.title}")
    print(f"  Status: {document.status}")
    print(f"  Chunk count: {document.chunk_count}")
    print(f"  File type: {document.file_type}")
    print(f"  Content hash: {document.content_hash}")
    print(f"{'='*80}")

    # Assertions
    assert document.id is not None
    assert document.status == "completed"
    assert document.chunk_count > 0, "Should have created at least 1 chunk"
    assert document.file_type == "markdown"
    assert document.content_hash is not None

    # Fetch chunks from database
    chunk_repo = ChunkRepository(SupabaseClient.get_client())
    chunks = await chunk_repo.get_by_document_id(
        document_id=document.id,
        user_id=test_user_id,  # Already a string
    )

    print(f"\nCHUNKS RETRIEVED FROM DATABASE:")
    print(f"  Total chunks: {len(chunks)}")

    # Validate chunks
    assert len(chunks) == document.chunk_count, "Chunk count mismatch"
    assert len(chunks) > 0, "Should have at least one chunk"

    # Validate first chunk
    first_chunk = chunks[0]
    print(f"\nFIRST CHUNK DETAILS:")
    print(f"  ID: {first_chunk.id}")
    print(f"  Index: {first_chunk.chunk_index}")
    print(f"  Type: {first_chunk.chunk_type}")
    print(f"  Content length: {len(first_chunk.content)} chars")
    print(f"  Embedding dimensions: {len(first_chunk.embedding)}")
    print(f"  Content preview: {first_chunk.content[:100]}...")

    # Validate embedding
    assert first_chunk.embedding is not None, "Chunk should have embedding"
    assert len(
        first_chunk.embedding) == 1536, "Should be OpenAI text-embedding-3-small (1536 dims)"
    assert all(isinstance(x, float)
               for x in first_chunk.embedding), "Embedding should be list of floats"

    # Validate metadata
    assert first_chunk.metadata is not None, "Chunk should have metadata"
    assert "source" in first_chunk.metadata, "Should preserve source metadata"
    assert first_chunk.metadata["source"] == "convex-docs"

    print(f"\n{'='*80}")
    print("✅ INTEGRATION TEST PASSED")
    print(f"{'='*80}\n")

    return document


@pytest.mark.asyncio
async def test_duplicate_detection(pipeline, test_user_id, progress_tracker):
    """
    Test that duplicate documents are detected and not re-processed.

    This test:
    1. Ingests a document once
    2. Tries to ingest the same document again
    3. Verifies that the second call returns the existing document
    4. Verifies that no new chunks were created
    """
    # Read test file
    with open(TEST_FILE, "rb") as f:
        file_bytes = f.read()

    print(f"\n{'='*80}")
    print(f"DUPLICATE DETECTION TEST")
    print(f"{'='*80}")

    # First ingestion
    print("\n[1] First ingestion (should create new document)...")
    doc1 = await pipeline.ingest_document(
        file_bytes=file_bytes,
        filename="test_duplicate.md",
        user_id=test_user_id,
        metadata={"test": True},
        progress_callback=progress_tracker,
    )

    first_chunk_count = doc1.chunk_count
    print(f"  Created document {doc1.id} with {first_chunk_count} chunks")

    # Second ingestion (same content, should be deduplicated)
    print("\n[2] Second ingestion (should return existing document)...")
    doc2 = await pipeline.ingest_document(
        file_bytes=file_bytes,
        filename="test_duplicate.md",  # Same filename
        user_id=test_user_id,
        metadata={"test": True},
        progress_callback=progress_tracker,
    )

    print(f"  Returned document {doc2.id}")

    # Validate deduplication
    assert doc1.id == doc2.id, "Should return same document ID"
    assert doc2.chunk_count == first_chunk_count, "Chunk count should be unchanged"

    print(f"\n✅ DUPLICATE DETECTION WORKS")
    print(f"{'='*80}\n")


@pytest.mark.asyncio
async def test_multiple_documents(pipeline, test_user_id, progress_tracker):
    """
    Test ingesting multiple different documents.

    This validates:
    - Pipeline can handle multiple documents
    - Each document gets unique ID
    - Chunks are correctly associated with their parent documents
    """
    # Get all test files from convex docs
    test_files = [
        TEST_DATA_DIR / "convex" / "mutations.md",
        TEST_DATA_DIR / "convex" / "queries.md",
    ]

    print(f"\n{'='*80}")
    print(f"MULTIPLE DOCUMENTS TEST")
    print(f"Ingesting {len(test_files)} documents")
    print(f"{'='*80}")

    documents = []

    for test_file in test_files:
        if not test_file.exists():
            print(f"⚠️  Skipping {test_file.name} (not found)")
            continue

        with open(test_file, "rb") as f:
            file_bytes = f.read()

        print(f"\nIngesting: {test_file.name}")
        doc = await pipeline.ingest_document(
            file_bytes=file_bytes,
            filename=test_file.name,
            user_id=test_user_id,
            metadata={"test": True},
            progress_callback=progress_tracker,
        )

        print(f"  ✓ Created {doc.id} with {doc.chunk_count} chunks")
        documents.append(doc)

    # Validate
    assert len(documents) >= 1, "Should have ingested at least 1 document"

    # Check that all documents have unique IDs
    doc_ids = [doc.id for doc in documents]
    assert len(doc_ids) == len(
        set(doc_ids)), "All documents should have unique IDs"

    # Check that all documents have chunks
    for doc in documents:
        assert doc.chunk_count > 0, f"Document {doc.id} should have chunks"

    print(f"\n✅ MULTIPLE DOCUMENTS TEST PASSED")
    print(f"Total documents ingested: {len(documents)}")
    print(f"Total chunks created: {sum(d.chunk_count for d in documents)}")
    print(f"{'='*80}\n")


# ============================================================================
# MAIN
# ============================================================================


if __name__ == "__main__":
    """
    Run tests directly without pytest.

    Useful for quick debugging:
    ```bash
    python tests/test_ingestion_pipeline_integration.py
    ```
    """
    print("\n🧪 Running integration tests...\n")

    async def run_tests():
        # Create fixtures
        supabase = SupabaseClient.get_client()
        doc_repo = DocumentRepository(supabase)
        chunk_repo = ChunkRepository(supabase)
        embedding_client = await get_embedding_client()

        pipeline = IngestionPipeline(
            doc_repo=doc_repo,
            chunk_repo=chunk_repo,
            embedding_client=embedding_client,
        )

        # Create test user
        test_user_id = uuid4()
        try:
            result = supabase.table("users").insert({
                "id": str(test_user_id),
                "email": f"test_{test_user_id}@example.com",
            }).execute()
            print(f"\n✅ Created test user: {test_user_id}")
        except Exception as e:
            print(f"\n❌ Failed to create test user: {e}")
            raise

        def progress_callback(state: dict) -> None:
            print(
                f"[PROGRESS] {state['stage']} ({state['percentage']:.1f}%) - {state['message']}")

        try:
            # Run tests
            print("\n" + "="*80)
            print("TEST 1: Ingest Real Document")
            print("="*80)
            await test_ingest_real_document(pipeline, test_user_id, progress_callback)

            print("\n" + "="*80)
            print("TEST 2: Duplicate Detection")
            print("="*80)
            await test_duplicate_detection(pipeline, test_user_id, progress_callback)

            print("\n" + "="*80)
            print("TEST 3: Multiple Documents")
            print("="*80)
            await test_multiple_documents(pipeline, test_user_id, progress_callback)

            print("\n✅ ALL TESTS PASSED!\n")

        finally:
            # Cleanup test user
            try:
                supabase.table("users").delete().eq(
                    "id", str(test_user_id)).execute()
                print(f"\n🧹 Cleaned up test user: {test_user_id}")
            except Exception as e:
                print(f"\n⚠️  Failed to cleanup: {e}")

    asyncio.run(run_tests())
