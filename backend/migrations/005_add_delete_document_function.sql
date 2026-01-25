-- ============================================================================
-- Migration 005: Add Atomic Document Deletion Function
-- ============================================================================
-- 
-- Purpose:
-- Provide atomic (transactional) deletion of documents and their chunks.
-- Ensures all-or-nothing behavior - no orphaned chunks or partial deletes.
--
-- Why PostgreSQL RPC instead of client-side transactions?
-- - Supabase Python client doesn't support explicit transactions
-- - PostgreSQL functions run in implicit transaction blocks
-- - Single round-trip to database (better performance)
-- - RLS policies are automatically enforced (SECURITY INVOKER)
-- - Consistent with Supabase's own auth functions
--
-- Usage:
-- SELECT * FROM delete_document_with_chunks('document-uuid-here');
--
-- Returns:
-- {
--   "deleted": true,
--   "document_id": "uuid",
--   "chunks_deleted": 42,
--   "user_id": "test_user_123"
-- }
--
-- Error Handling:
-- - Returns deleted=false if document not found
-- - Raises exception on permission errors (RLS)
-- - Automatic rollback on any error
--
-- Author: Integration Forge Team
-- Date: 2026-01-24
-- Phase: 5 (API Endpoints)
-- ============================================================================

BEGIN;

-- ============================================================================
-- FUNCTION: delete_document_with_chunks
-- ============================================================================
-- Atomically delete a document and all its chunks with RLS enforcement.
--
-- Parameters:
--   doc_id: UUID of the document to delete
--
-- Returns:
--   JSON object with deletion results:
--   - deleted: boolean (true if document was found and deleted)
--   - document_id: UUID of the deleted document
--   - chunks_deleted: integer count of deleted chunks
--   - user_id: owner of the deleted document
--
-- Security:
-- - SECURITY INVOKER ensures RLS policies apply with caller's permissions
-- - Only the document owner can delete (enforced by RLS)
-- - Cannot delete other users' documents
--
-- Transaction Behavior:
-- - All operations run in a single transaction
-- - If chunks delete fails, document delete is rolled back
-- - If document delete fails, chunk deletes are rolled back
-- - ATOMIC: either everything succeeds or everything fails
--
-- Learning Note:
-- Why SECURITY INVOKER?
-- - Function runs with the caller's user_id (from JWT)
-- - RLS policies automatically filter by auth.uid()
-- - Without it, function would run as database owner (bypass RLS)
-- - This is critical for multi-tenant security!

CREATE OR REPLACE FUNCTION delete_document_with_chunks(doc_id UUID)
RETURNS JSON
LANGUAGE plpgsql
SECURITY INVOKER  -- Run with caller's permissions (RLS enforced)
AS $$
DECLARE
    chunks_deleted_count INTEGER := 0;
    doc_deleted BOOLEAN := FALSE;
    doc_user_id TEXT;
    doc_title TEXT;
BEGIN
    -- Step 1: Verify document exists and get metadata
    -- RLS automatically filters to only documents owned by caller
    SELECT user_id, title INTO doc_user_id, doc_title
    FROM documents
    WHERE id = doc_id;
    
    -- If no document found (either doesn't exist or not owned by caller)
    IF NOT FOUND THEN
        RETURN json_build_object(
            'deleted', FALSE,
            'document_id', doc_id,
            'chunks_deleted', 0,
            'error', 'Document not found or access denied'
        );
    END IF;
    
    -- Step 2: Delete all chunks for this document
    -- RLS ensures only caller's chunks are deleted
    -- ON DELETE CASCADE would handle this, but we want explicit count
    DELETE FROM document_chunks WHERE document_id = doc_id;
    GET DIAGNOSTICS chunks_deleted_count = ROW_COUNT;
    
    -- Step 3: Delete the document itself
    -- RLS ensures only caller's document is deleted
    DELETE FROM documents WHERE id = doc_id;
    -- Use FOUND variable to check if deletion occurred
    doc_deleted := FOUND;
    
    -- Step 4: Return success stats
    -- If we got here, transaction succeeded (no exceptions)
    RETURN json_build_object(
        'deleted', doc_deleted,
        'document_id', doc_id,
        'chunks_deleted', chunks_deleted_count,
        'user_id', doc_user_id,
        'title', doc_title
    );
    
EXCEPTION
    -- Catch any errors and rollback entire transaction
    WHEN OTHERS THEN
        -- RAISE will rollback the transaction and propagate error to client
        RAISE EXCEPTION 'Failed to delete document %: %', doc_id, SQLERRM;
END;
$$;

-- Grant execute permission to authenticated users
-- Note: RLS policies inside function still enforce ownership
GRANT EXECUTE ON FUNCTION delete_document_with_chunks(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION delete_document_with_chunks(UUID) TO anon;

-- Add helpful comment for documentation
COMMENT ON FUNCTION delete_document_with_chunks(UUID) IS 
'Atomically delete a document and all its chunks. Returns JSON with deletion stats. RLS enforced - only document owner can delete.';

DO $$
BEGIN
    RAISE NOTICE 'Created delete_document_with_chunks() function with RLS enforcement';
    RAISE NOTICE 'Usage: SELECT * FROM delete_document_with_chunks(''uuid-here'')';
END $$;

COMMIT;


-- ============================================================================
-- TESTING NOTES
-- ============================================================================
-- 
-- Test Case 1: Successful deletion
-- SELECT * FROM delete_document_with_chunks('valid-doc-uuid');
-- Expected: {"deleted": true, "chunks_deleted": N, ...}
--
-- Test Case 2: Document not found
-- SELECT * FROM delete_document_with_chunks('00000000-0000-0000-0000-000000000000');
-- Expected: {"deleted": false, "error": "Document not found or access denied"}
--
-- Test Case 3: Permission denied (different user)
-- -- As user A, try to delete user B's document
-- Expected: {"deleted": false, "error": "Document not found or access denied"}
--
-- Test Case 4: Rollback on error
-- -- Simulate error after chunks deleted (e.g., trigger failure on documents table)
-- Expected: EXCEPTION raised, NO chunks deleted (rollback verified)
--
-- ============================================================================
