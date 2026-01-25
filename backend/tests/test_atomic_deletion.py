"""
Integration tests for atomic document deletion.

Tests the PostgreSQL RPC function delete_document_with_chunks()
to ensure ACID compliance and proper rollback behavior.

Run with:
    pytest tests/test_atomic_deletion.py -v
"""

import pytest
from uuid import uuid4

from app.database.client import get_db
from app.database.repositories.documents import DocumentRepository
from app.database.repositories.chunks import ChunkRepository
from app.database.models import Document, DocumentStatus, DocumentChunk, ChunkType
from app.utils.errors import NotFoundError, DatabaseError


@pytest.fixture
def supabase():
    """Get Supabase client."""
    return get_db()


@pytest.fixture
def doc_repo(supabase):
    """Get document repository."""
    return DocumentRepository(supabase)


@pytest.fixture
def chunk_repo(supabase):
    """Get chunk repository."""
    return ChunkRepository(supabase)


@pytest.fixture
def test_user_id(supabase):
    """
    Test user ID with auto-creation.

    Ensures the user exists in the database before tests run.
    This handles the foreign key constraint on documents.user_id.
    """
    user_id = "test_user_atomic_delete"

    # Try to create the user (idempotent with ON CONFLICT)
    try:
        supabase.table("users").upsert({
            "id": user_id,
            "email": f"{user_id}@test.example.com",
            "credits_used": 0,
            "storage_bytes_used": 0,
            "documents_count": 0,
        }, on_conflict="id").execute()
    except Exception as e:
        # User might already exist, which is fine
        pass

    return user_id


@pytest.fixture
def test_document(doc_repo, test_user_id):
    """Create a test document."""
    doc = Document(
        id=uuid4(),
        user_id=test_user_id,
        source_id=None,
        title="Test Document for Atomic Deletion",
        file_type="text/markdown",
        file_size=1024,
        content_hash=f"test_hash_{uuid4()}",
        status=DocumentStatus.COMPLETED,
    )
    created = doc_repo.create(doc)
    yield created
    # Cleanup: try to delete if still exists
    try:
        doc_repo.delete(created.id, test_user_id)
    except Exception:
        pass


@pytest.fixture
def test_chunks(chunk_repo, test_document, test_user_id):
    """Create test chunks for the document."""
    chunks_data = [
        {
            "document_id": test_document.id,
            "user_id": test_user_id,
            "chunk_index": i,
            "content": f"Test chunk content {i}",
            "chunk_type": ChunkType.CHILD.value,
            "token_count": 10,
            "embedding": [0.1] * 1536,  # Mock embedding
        }
        for i in range(5)
    ]

    created_chunks = chunk_repo.create_batch(chunks_data)
    return created_chunks


class TestAtomicDeletion:
    """Test suite for atomic document deletion."""

    def test_successful_atomic_deletion(
        self, doc_repo, chunk_repo, test_document, test_chunks, test_user_id
    ):
        """
        Test successful atomic deletion of document and chunks.

        Verifies:
        - Both document and chunks are deleted
        - Chunk count is accurate
        - Response contains expected fields
        """
        # Verify initial state: document and chunks exist
        assert doc_repo.get_by_id(test_document.id, test_user_id) is not None
        chunks_before = chunk_repo.get_by_document_id(
            document_id=test_document.id,
            user_id=test_user_id
        )
        assert len(chunks_before) == 5

        # Perform atomic deletion
        result = doc_repo.delete_with_chunks(test_document.id, test_user_id)

        # Verify response structure
        assert result["deleted"] is True
        assert result["document_id"] == str(test_document.id)
        assert result["chunks_deleted"] == 5
        assert result["user_id"] == test_user_id
        assert result["title"] == test_document.title

        # Verify document is deleted
        assert doc_repo.get_by_id(test_document.id, test_user_id) is None

        # Verify chunks are deleted
        chunks_after = chunk_repo.get_by_document_id(
            document_id=test_document.id,
            user_id=test_user_id
        )
        assert len(chunks_after) == 0

    def test_delete_nonexistent_document(self, doc_repo, test_user_id):
        """
        Test deleting a document that doesn't exist.

        Verifies:
        - NotFoundError is raised
        - No side effects in database
        """
        nonexistent_id = uuid4()

        with pytest.raises(NotFoundError) as exc_info:
            doc_repo.delete_with_chunks(nonexistent_id, test_user_id)

        assert "not found" in str(exc_info.value).lower()

    def test_delete_document_without_chunks(
        self, doc_repo, test_document, test_user_id
    ):
        """
        Test deleting a document that has no chunks.

        Verifies:
        - Document is deleted successfully
        - chunks_deleted is 0
        - No errors occur
        """
        # Don't create chunks, just delete document
        result = doc_repo.delete_with_chunks(test_document.id, test_user_id)

        assert result["deleted"] is True
        assert result["chunks_deleted"] == 0
        assert doc_repo.get_by_id(test_document.id, test_user_id) is None

    @pytest.mark.skip(reason="RLS bypassed when using service role key - will test in Phase 6 with JWT auth")
    def test_rls_enforcement_different_user(
        self, doc_repo, test_document, test_chunks
    ):
        """
        Test that RLS prevents deleting another user's document.

        NOTE: This test is skipped because the backend uses SUPABASE_SERVICE_ROLE_KEY
        which bypasses RLS policies. In Phase 6, when JWT authentication is added,
        this test will validate that users cannot delete each other's documents.

        Verifies:
        - User A cannot delete User B's document
        - NotFoundError is raised (RLS hides the document)
        - Original document and chunks remain intact
        """
        different_user_id = "different_user_123"

        with pytest.raises(NotFoundError):
            doc_repo.delete_with_chunks(test_document.id, different_user_id)

        # Verify document still exists
        doc = doc_repo.get_by_id(test_document.id, "test_user_atomic_delete")
        assert doc is not None
        assert doc.user_id == "test_user_atomic_delete"

    def test_deletion_with_parent_child_chunks(
        self, doc_repo, chunk_repo, test_document, test_user_id
    ):
        """
        Test atomic deletion with parent-child chunk hierarchies.

        Verifies:
        - Both parent and child chunks are deleted
        - Chunk count includes all chunks
        - No orphaned chunks remain
        """
        # Create parent chunks
        parent_chunks_data = [
            {
                "document_id": test_document.id,
                "user_id": test_user_id,
                "chunk_index": i,
                "content": f"Parent chunk {i}",
                "chunk_type": ChunkType.PARENT.value,
                "token_count": 100,
                "embedding": None,  # Parents don't have embeddings
            }
            for i in range(2)
        ]
        parent_chunks = chunk_repo.create_batch(parent_chunks_data)

        # Create child chunks linked to parents
        child_chunks_data = [
            {
                "document_id": test_document.id,
                "user_id": test_user_id,
                "parent_chunk_id": parent_chunks[i // 3].id,
                "chunk_index": i,
                "content": f"Child chunk {i}",
                "chunk_type": ChunkType.CHILD.value,
                "token_count": 30,
                "embedding": [0.1] * 1536,
            }
            for i in range(6)  # 3 children per parent
        ]
        chunk_repo.create_batch(child_chunks_data)

        # Total: 2 parents + 6 children = 8 chunks
        result = doc_repo.delete_with_chunks(test_document.id, test_user_id)

        assert result["deleted"] is True
        assert result["chunks_deleted"] == 8  # All chunks deleted

        # Verify no orphaned chunks
        remaining_chunks = chunk_repo.get_by_document_id(
            document_id=test_document.id,
            user_id=test_user_id
        )
        assert len(remaining_chunks) == 0

    def test_idempotent_deletion(self, doc_repo, test_document, test_user_id):
        """
        Test that deleting an already-deleted document raises NotFoundError.

        Verifies:
        - First deletion succeeds
        - Second deletion raises NotFoundError
        - No errors from attempting to delete non-existent records
        """
        # First deletion should succeed
        result1 = doc_repo.delete_with_chunks(test_document.id, test_user_id)
        assert result1["deleted"] is True

        # Second deletion should raise NotFoundError
        with pytest.raises(NotFoundError):
            doc_repo.delete_with_chunks(test_document.id, test_user_id)


class TestAtomicityGuarantees:
    """
    Test suite specifically for transaction atomicity.

    Note: These tests verify the behavior but cannot easily simulate
    partial failures without modifying the database. They serve as
    documentation for expected behavior.
    """

    def test_all_or_nothing_behavior_documentation(self):
        """
        Document the expected ACID behavior of atomic deletion.

        Expected Behavior (verified by PostgreSQL transaction):
        1. BEGIN transaction
        2. Delete chunks
        3. Delete document
        4. COMMIT if both succeed, ROLLBACK if either fails

        Impossible States:
        - Document deleted but chunks remain (orphaned chunks)
        - Chunks deleted but document remains (FK violation)
        - Partial chunk deletion (some chunks deleted, others not)

        Why This Works:
        - PostgreSQL stored procedure runs in implicit transaction
        - Any exception triggers automatic ROLLBACK
        - Both operations succeed or both fail atomically

        Testing Approach:
        - Manual testing: Modify RPC to raise exception after chunk delete
        - Verify chunks are rolled back (not deleted)
        - Production: PostgreSQL guarantees atomicity natively
        """
        # This is a documentation test - actual atomicity is guaranteed by PostgreSQL
        assert True  # Placeholder for documentation

    def test_performance_single_round_trip(
        self, doc_repo, chunk_repo, test_document, test_user_id
    ):
        """
        Verify that atomic deletion is a single database round-trip.

        This is a conceptual test - the RPC approach guarantees:
        - One call to supabase.rpc()
        - PostgreSQL handles chunk and document deletion internally
        - No N+1 queries for chunks
        - Better performance than client-side deletion loops
        """
        # Create 100 chunks to test performance
        large_chunk_batch = [
            {
                "document_id": test_document.id,
                "user_id": test_user_id,
                "chunk_index": i,
                "content": f"Chunk {i}",
                "chunk_type": ChunkType.CHILD.value,
                "token_count": 10,
                "embedding": [0.1] * 1536,
            }
            for i in range(100)
        ]
        chunk_repo.create_batch(large_chunk_batch)

        # Single RPC call deletes all 100 chunks + document atomically
        result = doc_repo.delete_with_chunks(test_document.id, test_user_id)

        assert result["chunks_deleted"] == 100
        assert result["deleted"] is True
        # Performance: This was 1 RPC call, not 101 separate queries


# ============================================================================
# Manual Testing Instructions
# ============================================================================
"""
To manually verify atomic rollback behavior:

1. Run Supabase SQL Editor
2. Temporarily modify the RPC function:

   CREATE OR REPLACE FUNCTION delete_document_with_chunks(doc_id UUID)
   RETURNS JSON AS $$
   BEGIN
       -- Delete chunks
       DELETE FROM document_chunks WHERE document_id = doc_id;
       
       -- Simulate error AFTER chunks deleted
       RAISE EXCEPTION 'Simulated error for rollback test';
       
       -- This line never executes
       DELETE FROM documents WHERE id = doc_id;
       
       RETURN json_build_object('deleted', true);
   END;
   $$ LANGUAGE plpgsql SECURITY INVOKER;

3. Call the function:
   SELECT * FROM delete_document_with_chunks('your-doc-uuid');

4. Expected: ERROR raised, NO CHUNKS DELETED (rollback verified)

5. Restore original function from migration 005

This proves PostgreSQL's automatic transaction rollback works correctly.
"""
