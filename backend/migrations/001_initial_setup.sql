-- ============================================================================
-- Integration Forge - Initial Database Setup
-- ============================================================================
-- 
-- This migration creates the complete database schema for the RAG system.
-- 
-- LEARNING NOTES:
-- - This file is idempotent (can be run multiple times safely)
-- - Uses CASCADE on drops (careful in production!)
-- - pgvector extension enables vector similarity search
-- - RLS (Row-Level Security) enforces user data isolation
-- - HNSW index enables fast approximate nearest neighbor search
--
-- HOW TO RUN:
-- 1. Open Supabase Dashboard → SQL Editor
-- 2. Paste this entire file
-- 3. Click "Run" or press Cmd/Ctrl + Enter
-- 4. Verify success in Table Editor
-- ============================================================================


-- ============================================================================
-- SECTION 1: EXTENSIONS
-- ============================================================================
-- Extensions add functionality to PostgreSQL beyond core features.

-- Enable UUID generation for primary keys
-- Learning Note: UUIDs are better than auto-increment IDs because:
-- - Globally unique (safe in distributed systems)
-- - Hard to guess (security)
-- - Can be generated client-side
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable vector operations for embeddings
-- Learning Note: pgvector adds the VECTOR data type and similarity operators
-- - Stores dense vectors (arrays of floats)
-- - Provides distance functions: <-> (L2), <#> (inner product), <=> (cosine)
-- - Enables HNSW and IVFFlat indexes for fast search
CREATE EXTENSION IF NOT EXISTS vector;


-- ============================================================================
-- SECTION 2: DROP EXISTING TABLES (Development Only)
-- ============================================================================
-- Warning: This deletes all data! Only use during initial setup.
-- In production, use ALTER TABLE for schema changes.

DROP TABLE IF EXISTS document_chunks CASCADE;
DROP TABLE IF EXISTS documents CASCADE;
DROP TABLE IF EXISTS sources CASCADE;
DROP TABLE IF EXISTS users CASCADE;


-- ============================================================================
-- SECTION 3: CREATE TABLES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- TABLE: users
-- ----------------------------------------------------------------------------
-- Stores user information from Clerk authentication.
-- This is a local mirror for performance (avoid external API calls).
--
-- Learning Note: 
-- - id is TEXT (not UUID) because Clerk uses custom format: "user_2b..."
-- - Storage tracking for quota enforcement (100MB free tier)
-- - credits_used for rate limiting and billing
CREATE TABLE users (
    -- Primary key: Clerk user ID (e.g., "user_2bXYZ123")
    id TEXT PRIMARY KEY,
    
    -- User identification
    email TEXT NOT NULL UNIQUE,
    
    -- Quota tracking for free tier limits
    credits_used INTEGER NOT NULL DEFAULT 0,
    storage_bytes_used BIGINT NOT NULL DEFAULT 0,
    documents_count INTEGER NOT NULL DEFAULT 0,
    last_quota_reset TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Learning Note: Create index on email for fast lookups during login
CREATE INDEX idx_users_email ON users(email);


-- ----------------------------------------------------------------------------
-- TABLE: sources
-- ----------------------------------------------------------------------------
-- Logical containers for documents (like folders).
-- Example: "LangGraph Docs", "Stripe API Reference"
--
-- Learning Note:
-- - Each user can have multiple sources
-- - Sources help organize documents by topic/project
-- - The AI agent can use source descriptions for context
CREATE TABLE sources (
    -- Primary key: Auto-generated UUID
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Owner of this source
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Source metadata
    name TEXT NOT NULL CHECK (length(name) >= 1 AND length(name) <= 255),
    description TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Learning Note: Index on user_id for fast "show my sources" queries
CREATE INDEX idx_sources_user_id ON sources(user_id);


-- ----------------------------------------------------------------------------
-- TABLE: documents
-- ----------------------------------------------------------------------------
-- Represents a file uploaded by a user (Markdown, PDF, etc.).
-- The actual file content is stored in Supabase Storage (blob_path).
--
-- Processing Workflow:
-- 1. User uploads file → status = 'pending'
-- 2. Backend parses → status = 'processing'  
-- 3. Backend chunks and embeds → status = 'completed' or 'failed'
--
-- Learning Note:
-- - user_id is denormalized (duplicated from sources) for RLS performance
-- - hash prevents duplicate uploads (SHA256 of content)
-- - status is an ENUM-like CHECK constraint
CREATE TABLE documents (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Relationships
    source_id UUID NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Document metadata
    title TEXT NOT NULL CHECK (length(title) >= 1 AND length(title) <= 500),
    blob_path TEXT NOT NULL,
    token_count INTEGER NOT NULL DEFAULT 0 CHECK (token_count >= 0),
    hash TEXT,
    
    -- Processing status (enum-like constraint)
    status TEXT NOT NULL DEFAULT 'pending' 
        CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Learning Note: Composite index for "show documents in this source" queries
CREATE INDEX idx_documents_source_id ON documents(source_id);
CREATE INDEX idx_documents_user_id ON documents(user_id);
CREATE INDEX idx_documents_status ON documents(status);
-- Unique index on hash to prevent duplicate uploads
CREATE INDEX idx_documents_hash ON documents(hash) WHERE hash IS NOT NULL;


-- ----------------------------------------------------------------------------
-- TABLE: document_chunks
-- ----------------------------------------------------------------------------
-- THE CORE OF THE RAG SYSTEM!
-- Each chunk is a piece of text from a document with its vector embedding.
--
-- Key Fields:
-- - content: The actual text (what the AI will reference)
-- - embedding: 1536-dimensional vector from OpenAI text-embedding-3-small
-- - metadata: JSONB for flexible context (headers, page numbers, etc.)
--
-- Parent-Child Chunking:
-- - PARENT chunks: Large context (not embedded)
-- - CHILD chunks: Small searchable chunks (embedded)
-- - parent_chunk_id links child to parent
--
-- Learning Note:
-- - VECTOR(1536) is the pgvector data type
-- - 1536 dimensions is the industry standard (95% accuracy of 3072, 15% cost)
-- - HNSW index works best with ≤2000 dimensions (pgvector limitation)
-- - JSONB allows flexible schema for different document types
-- - chunk_index preserves document order for context reconstruction
CREATE TABLE document_chunks (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Relationships
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    parent_chunk_id UUID REFERENCES document_chunks(id) ON DELETE CASCADE,
    
    -- Chunk data
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    content TEXT NOT NULL CHECK (length(content) >= 1),
    
    -- Flexible metadata storage (JSONB)
    -- Example: {"header": "Auth", "page": 5, "language": "typescript"}
    metadata JSONB NOT NULL DEFAULT '{}',
    
    -- Vector embedding for semantic search
    -- Learning Note: 1536 dimensions for OpenAI text-embedding-3-small
    -- NULL until embedding is generated (async process)
    embedding VECTOR(1536),
    
    -- Chunk type for parent-child strategy
    chunk_type TEXT NOT NULL DEFAULT 'parent'
        CHECK (chunk_type IN ('parent', 'child')),
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Learning Note: These indexes are CRITICAL for performance!

-- 1. Document lookup: "get all chunks for this document"
CREATE INDEX idx_chunks_document_id ON document_chunks(document_id);

-- 2. RLS filtering: "get chunks for this user"
CREATE INDEX idx_chunks_user_id ON document_chunks(user_id);

-- 3. Order preservation: "get chunks in sequence"
CREATE INDEX idx_chunks_document_order ON document_chunks(document_id, chunk_index);

-- 4. Parent-child navigation: "get children of this parent"
CREATE INDEX idx_chunks_parent_id ON document_chunks(parent_chunk_id) 
    WHERE parent_chunk_id IS NOT NULL;

-- 5. HNSW Vector Index - THE MOST IMPORTANT INDEX!
-- Learning Note: HNSW (Hierarchical Navigable Small World) is a graph-based algorithm
-- - Enables fast approximate nearest neighbor search
-- - m=16: number of connections per layer (higher = better recall, slower build)
-- - ef_construction=64: size of dynamic candidate list (higher = better quality)
-- - Uses cosine distance (<=>): best for normalized embeddings
-- - Only indexes non-NULL embeddings (WHERE clause)
CREATE INDEX idx_chunks_embedding_hnsw ON document_chunks 
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64)
    WHERE embedding IS NOT NULL;

-- 6. JSONB Index for metadata queries
-- Learning Note: GIN (Generalized Inverted Index) enables fast JSONB queries
-- - Can search for specific keys: metadata @> '{"language": "typescript"}'
-- - Can check key existence: metadata ? 'header'
CREATE INDEX idx_chunks_metadata ON document_chunks USING GIN (metadata);


-- ============================================================================
-- SECTION 4: ROW-LEVEL SECURITY (RLS)
-- ============================================================================
-- RLS automatically filters queries based on the current user.
-- This ensures users can ONLY see their own data.
--
-- Learning Note: How RLS Works
-- 1. Backend authenticates user → gets JWT token
-- 2. Backend sets PostgreSQL session variable: current_setting('request.jwt.claims')
-- 3. RLS policies check: user_id = (JWT claim ->> 'sub')
-- 4. PostgreSQL automatically filters all queries
--
-- Security Model:
-- - Service role (backend): BYPASSES RLS (has full access)
-- - Authenticated users: Filtered by RLS policies
-- - Anonymous users: NO ACCESS (not implemented yet)

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;

-- ----------------------------------------------------------------------------
-- RLS POLICY: users table
-- ----------------------------------------------------------------------------
-- Users can only see their own user record

CREATE POLICY "Users can view own record"
    ON users
    FOR SELECT
    USING (id = current_setting('request.jwt.claims', true)::json->>'sub');

CREATE POLICY "Users can update own record"
    ON users
    FOR UPDATE
    USING (id = current_setting('request.jwt.claims', true)::json->>'sub');

-- Learning Note: Service role bypasses RLS, so backend can create users

-- ----------------------------------------------------------------------------
-- RLS POLICY: sources table
-- ----------------------------------------------------------------------------
-- Users can only see/modify their own sources

CREATE POLICY "Users can view own sources"
    ON sources
    FOR SELECT
    USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

CREATE POLICY "Users can insert own sources"
    ON sources
    FOR INSERT
    WITH CHECK (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

CREATE POLICY "Users can update own sources"
    ON sources
    FOR UPDATE
    USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

CREATE POLICY "Users can delete own sources"
    ON sources
    FOR DELETE
    USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

-- ----------------------------------------------------------------------------
-- RLS POLICY: documents table
-- ----------------------------------------------------------------------------
-- Users can only see/modify their own documents

CREATE POLICY "Users can view own documents"
    ON documents
    FOR SELECT
    USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

CREATE POLICY "Users can insert own documents"
    ON documents
    FOR INSERT
    WITH CHECK (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

CREATE POLICY "Users can update own documents"
    ON documents
    FOR UPDATE
    USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

CREATE POLICY "Users can delete own documents"
    ON documents
    FOR DELETE
    USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

-- ----------------------------------------------------------------------------
-- RLS POLICY: document_chunks table
-- ----------------------------------------------------------------------------
-- Users can only see/modify their own chunks
-- This is the MOST IMPORTANT policy (protects the vector store)

CREATE POLICY "Users can view own chunks"
    ON document_chunks
    FOR SELECT
    USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

CREATE POLICY "Users can insert own chunks"
    ON document_chunks
    FOR INSERT
    WITH CHECK (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

CREATE POLICY "Users can update own chunks"
    ON document_chunks
    FOR UPDATE
    USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

CREATE POLICY "Users can delete own chunks"
    ON document_chunks
    FOR DELETE
    USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub');


-- ============================================================================
-- SECTION 5: TRIGGERS
-- ============================================================================
-- Triggers automatically run functions when data changes.

-- ----------------------------------------------------------------------------
-- Trigger: Auto-update updated_at timestamp
-- ----------------------------------------------------------------------------
-- Learning Note: This ensures updated_at is always current

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to all tables
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sources_updated_at
    BEFORE UPDATE ON sources
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_chunks_updated_at
    BEFORE UPDATE ON document_chunks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ============================================================================
-- SECTION 6: HELPER FUNCTIONS
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Function: Search document chunks by vector similarity
-- ----------------------------------------------------------------------------
-- Learning Note: This is a stored procedure for vector search
-- - Uses cosine distance (1 - cosine_similarity)
-- - Returns top K most similar chunks
-- - Filters by user_id (respects RLS)
-- - Orders by similarity (distance ASC = most similar first)

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
    similarity FLOAT
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
        1 - (dc.embedding <=> query_embedding) AS similarity
    FROM document_chunks dc
    WHERE 
        dc.embedding IS NOT NULL
        AND (filter_user_id IS NULL OR dc.user_id = filter_user_id)
    ORDER BY dc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;


-- ============================================================================
-- SECTION 7: VERIFICATION
-- ============================================================================
-- These queries help verify the migration succeeded

-- Show all tables
SELECT tablename 
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY tablename;

-- Show all indexes
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

-- Show RLS policies
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual,
    with_check
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;


-- ============================================================================
-- MIGRATION COMPLETE!
-- ============================================================================
-- Next Steps:
-- 1. Verify tables exist in Supabase Table Editor
-- 2. Test inserting a user (using service role key)
-- 3. Proceed to Phase 2 Python code (schemas, repositories, etc.)
-- ============================================================================
