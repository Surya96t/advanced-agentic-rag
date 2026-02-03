-- Migration 007: Add document_title to search functions
-- 
-- This migration updates search functions to include the document title  
-- in search results, fixing the "Unknown Document" issue in frontend citations.
--
-- Changes:
-- - Drop and recreate search_chunks_by_embedding with document_title
-- - Drop and recreate search_chunks_by_text with document_title
-- - JOIN with documents table to fetch title in both functions
--
-- Rollback:
-- - Run the original function definitions from migrations 001 and 004

-- ============================================================================
-- Drop existing functions before recreating with new signature
-- ============================================================================

DROP FUNCTION IF EXISTS search_chunks_by_embedding(vector, integer, text);
DROP FUNCTION IF EXISTS search_chunks_by_text(text, integer, text, text);

-- ============================================================================
-- Recreate search_chunks_by_embedding with document_title
-- ============================================================================

CREATE OR REPLACE FUNCTION search_chunks_by_embedding(
    query_embedding VECTOR(1536),
    match_count INTEGER DEFAULT 10,
    filter_user_id TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    document_id UUID,
    content TEXT,
    metadata JSONB,
    similarity FLOAT,
    document_title TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        dc.id,
        dc.document_id,
        dc.content,
        dc.metadata,
        1 - (dc.embedding <=> query_embedding) AS similarity,
        d.title AS document_title
    FROM document_chunks dc
    INNER JOIN documents d ON dc.document_id = d.id
    WHERE 
        dc.embedding IS NOT NULL
        AND (filter_user_id IS NULL OR dc.user_id = filter_user_id)
    ORDER BY dc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- ============================================================================
-- Recreate search_chunks_by_text with document_title
-- ============================================================================

CREATE OR REPLACE FUNCTION search_chunks_by_text(
    query_text TEXT,
    match_count INTEGER DEFAULT 10,
    filter_user_id TEXT DEFAULT NULL,
    ranking_function TEXT DEFAULT 'ts_rank_cd'
)
RETURNS TABLE (
    id UUID,
    document_id UUID,
    content TEXT,
    metadata JSONB,
    rank REAL,
    document_title TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    tsquery_obj TSQUERY;
BEGIN
    tsquery_obj := plainto_tsquery('english', query_text);
    
    IF ranking_function = 'ts_rank_cd' THEN
        RETURN QUERY
        SELECT
            dc.id,
            dc.document_id,
            dc.content,
            dc.metadata,
            ts_rank_cd(dc.search_vector, tsquery_obj) AS rank,
            d.title AS document_title
        FROM document_chunks dc
        INNER JOIN documents d ON dc.document_id = d.id
        WHERE
            dc.search_vector @@ tsquery_obj
            AND (filter_user_id IS NULL OR dc.user_id = filter_user_id)
        ORDER BY rank DESC
        LIMIT match_count;
    ELSE
        RETURN QUERY
        SELECT
            dc.id,
            dc.document_id,
            dc.content,
            dc.metadata,
            ts_rank(dc.search_vector, tsquery_obj) AS rank,
            d.title AS document_title
        FROM document_chunks dc
        INNER JOIN documents d ON dc.document_id = d.id
        WHERE
            dc.search_vector @@ tsquery_obj
            AND (filter_user_id IS NULL OR dc.user_id = filter_user_id)
        ORDER BY rank DESC
        LIMIT match_count;
    END IF;
END;
$$;

-- ============================================================================
-- Verification
-- ============================================================================

-- Verify the functions exist with correct signatures
SELECT 
    routine_name,
    routine_type,
    data_type
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name IN ('search_chunks_by_embedding', 'search_chunks_by_text')
ORDER BY routine_name;

-- You can also verify by describing the return types:
-- \df search_chunks_by_embedding
-- \df search_chunks_by_text
