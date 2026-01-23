-- ============================================================================
-- Migration 004: Add Full-Text Search to document_chunks
-- ============================================================================
-- 
-- Purpose:
-- Enable hybrid search (dense vector + sparse text) by adding PostgreSQL
-- full-text search capabilities to the document_chunks table.
--
-- Changes:
-- 1. Add search_vector TSVECTOR column
-- 2. Create trigger to auto-generate tsvector from content
-- 3. Add GIN index for fast text search
-- 4. Backfill existing chunks
--
-- Performance:
-- - GIN index enables <50ms text search on millions of chunks
-- - Auto-update trigger adds ~1ms overhead per INSERT/UPDATE
-- - Index size: ~40% of content column size
--
-- Author: Integration Forge Team
-- Date: 2026-01-22
-- Phase: 3 (Retrieval System)
-- ============================================================================

BEGIN;

-- ============================================================================
-- STEP 1: Add search_vector Column
-- ============================================================================
-- TSVECTOR is PostgreSQL's data type for full-text search
-- It stores preprocessed, normalized tokens for fast matching

DO $$
BEGIN
    -- Check if column already exists (idempotent migration)
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'document_chunks' 
        AND column_name = 'search_vector'
    ) THEN
        ALTER TABLE document_chunks 
        ADD COLUMN search_vector TSVECTOR;
        
        RAISE NOTICE 'Added search_vector column to document_chunks';
    ELSE
        RAISE NOTICE 'search_vector column already exists, skipping';
    END IF;
END $$;


-- ============================================================================
-- STEP 2: Create Trigger Function for Auto-Update
-- ============================================================================
-- This function automatically generates the tsvector whenever content changes
-- 
-- Learning Note: Why use a trigger?
-- - Developers don't need to manually update search_vector
-- - Ensures search index is always in sync with content
-- - PostgreSQL's to_tsvector() handles:
--   - Lowercasing
--   - Stemming (running → run, ran → run)
--   - Stopword removal (the, a, an, etc.)
--   - Punctuation normalization

CREATE OR REPLACE FUNCTION update_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    -- Generate tsvector from content using English dictionary
    -- to_tsvector('english', text) processes text for full-text search
    NEW.search_vector := to_tsvector('english', COALESCE(NEW.content, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger that fires BEFORE INSERT or UPDATE
-- This ensures search_vector is populated before the row is written
DROP TRIGGER IF EXISTS update_search_vector_trigger ON document_chunks;

CREATE TRIGGER update_search_vector_trigger
    BEFORE INSERT OR UPDATE OF content
    ON document_chunks
    FOR EACH ROW
    EXECUTE FUNCTION update_search_vector();

DO $$
BEGIN
    RAISE NOTICE 'Created trigger for automatic search_vector updates';
END $$;


-- ============================================================================
-- STEP 3: Create GIN Index on search_vector
-- ============================================================================
-- GIN (Generalized Inverted Index) is optimized for full-text search
--
-- Learning Note: GIN vs GIST
-- - GIN: Faster queries (3x), slower updates, larger index (~40% of data)
-- - GIST: Slower queries, faster updates, smaller index (~20% of data)
-- - For RAG (read-heavy), GIN is the clear winner
--
-- Performance Impact:
-- - Without index: O(n) table scan (slow!)
-- - With GIN index: O(log n) lookup (fast!)
-- - Example: 1M chunks, search goes from 2000ms → 30ms

CREATE INDEX IF NOT EXISTS idx_chunks_search_vector 
    ON document_chunks 
    USING GIN (search_vector);

DO $$
BEGIN
    RAISE NOTICE 'Created GIN index on search_vector';
END $$;


-- ============================================================================
-- STEP 4: Backfill Existing Chunks
-- ============================================================================
-- Update all existing chunks to populate search_vector
-- The trigger will automatically generate tsvector from content

DO $$
DECLARE
    chunks_updated INTEGER;
BEGIN
    -- Update all chunks where search_vector is NULL
    -- The trigger will populate search_vector from content
    UPDATE document_chunks 
    SET content = content  -- Dummy update to fire trigger
    WHERE search_vector IS NULL;
    
    GET DIAGNOSTICS chunks_updated = ROW_COUNT;
    
    RAISE NOTICE 'Backfilled search_vector for % chunks', chunks_updated;
END $$;


-- ============================================================================
-- STEP 5: Add Helper Function for Text Search
-- ============================================================================
-- Stored procedure for text search with ranking
-- This complements the existing search_chunks_by_embedding() function

CREATE OR REPLACE FUNCTION search_chunks_by_text(
    query_text TEXT,
    match_count INTEGER DEFAULT 10,
    filter_user_id TEXT DEFAULT NULL,
    ranking_function TEXT DEFAULT 'ts_rank_cd'  -- 'ts_rank' or 'ts_rank_cd'
)
RETURNS TABLE (
    id UUID,
    document_id UUID,
    content TEXT,
    metadata JSONB,
    rank REAL
)
LANGUAGE plpgsql
AS $$
DECLARE
    tsquery_obj TSQUERY;
BEGIN
    -- Convert query text to tsquery (handles phrase matching, AND/OR)
    -- plainto_tsquery() is simpler than to_tsquery() and handles user input safely
    tsquery_obj := plainto_tsquery('english', query_text);
    
    -- Execute text search with ranking
    IF ranking_function = 'ts_rank_cd' THEN
        -- ts_rank_cd: Cover Density ranking (considers proximity of terms)
        RETURN QUERY
        SELECT
            dc.id,
            dc.document_id,
            dc.content,
            dc.metadata,
            ts_rank_cd(dc.search_vector, tsquery_obj)::REAL AS rank
        FROM document_chunks dc
        WHERE 
            dc.search_vector @@ tsquery_obj
            AND (filter_user_id IS NULL OR dc.user_id = filter_user_id)
        ORDER BY ts_rank_cd(dc.search_vector, tsquery_obj) DESC
        LIMIT match_count;
    ELSE
        -- ts_rank: Standard ranking (simpler, faster)
        RETURN QUERY
        SELECT
            dc.id,
            dc.document_id,
            dc.content,
            dc.metadata,
            ts_rank(dc.search_vector, tsquery_obj)::REAL AS rank
        FROM document_chunks dc
        WHERE 
            dc.search_vector @@ tsquery_obj
            AND (filter_user_id IS NULL OR dc.user_id = filter_user_id)
        ORDER BY ts_rank(dc.search_vector, tsquery_obj) DESC
        LIMIT match_count;
    END IF;
END;
$$;

DO $$
BEGIN
    RAISE NOTICE 'Created search_chunks_by_text() function';
END $$;


-- ============================================================================
-- STEP 6: Verify Migration
-- ============================================================================

DO $$
DECLARE
    total_chunks INTEGER;
    chunks_with_search_vector INTEGER;
BEGIN
    -- Count total chunks
    SELECT COUNT(*) INTO total_chunks FROM document_chunks;
    
    -- Count chunks with search_vector populated
    SELECT COUNT(*) INTO chunks_with_search_vector 
    FROM document_chunks 
    WHERE search_vector IS NOT NULL;
    
    RAISE NOTICE '=== Migration 004 Verification ===';
    RAISE NOTICE 'Total chunks: %', total_chunks;
    RAISE NOTICE 'Chunks with search_vector: %', chunks_with_search_vector;
    
    IF total_chunks > 0 AND chunks_with_search_vector = total_chunks THEN
        RAISE NOTICE 'SUCCESS: All chunks have search_vector populated';
    ELSIF total_chunks = 0 THEN
        RAISE NOTICE 'INFO: No chunks in database yet (expected for new setup)';
    ELSE
        RAISE WARNING 'ISSUE: % chunks missing search_vector', 
            (total_chunks - chunks_with_search_vector);
    END IF;
END $$;

COMMIT;

-- ============================================================================
-- Migration Complete!
-- ============================================================================
-- 
-- What was added:
-- ✅ search_vector TSVECTOR column
-- ✅ Auto-update trigger (fires on INSERT/UPDATE)
-- ✅ GIN index for fast text search
-- ✅ Backfilled existing chunks
-- ✅ search_chunks_by_text() helper function
--
-- How to test:
-- 
-- 1. Insert a test chunk and verify search_vector is auto-populated:
--    INSERT INTO document_chunks (document_id, user_id, chunk_index, content)
--    VALUES (
--        (SELECT id FROM documents LIMIT 1),
--        (SELECT id FROM users LIMIT 1),
--        999,
--        'This is a test chunk about PostgreSQL full-text search'
--    )
--    RETURNING id, search_vector;
--
-- 2. Test text search:
--    SELECT * FROM search_chunks_by_text('postgresql search', 5);
--
-- 3. Test hybrid search (vector + text) in Python code (Task 4)
--
-- Next steps:
-- - Task 2: Implement VectorSearcher in Python
-- - Task 3: Implement TextSearcher in Python
-- - Task 4: Implement HybridSearcher with RRF fusion
-- ============================================================================
