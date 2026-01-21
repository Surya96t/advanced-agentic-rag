-- Migration 002: Update Document Schema for Ingestion Pipeline
-- 
-- This migration aligns the database schema with the updated Document model
-- to support the ingestion pipeline requirements.
--
-- Changes:
-- 1. Rename hash → content_hash (clearer naming)
-- 2. Add file_type column (markdown, pdf, txt)
-- 3. Add file_size column (bytes)
-- 4. Add chunk_count column (track processing progress)
-- 5. Make source_id optional (NULL allowed)
-- 6. Make blob_path optional (NULL allowed)
-- 7. Update user_id to UUID type (from TEXT)
-- 8. Add metadata JSONB column (flexible metadata storage)
-- 9. Remove token_count (not needed for now)
--
-- Run this migration in Supabase SQL Editor or via CLI

-- Step 1: Rename hash to content_hash
ALTER TABLE documents 
RENAME COLUMN hash TO content_hash;

-- Step 2: Add new columns
ALTER TABLE documents 
ADD COLUMN IF NOT EXISTS file_type TEXT NOT NULL DEFAULT 'unknown',
ADD COLUMN IF NOT EXISTS file_size INTEGER NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS chunk_count INTEGER NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;

-- Step 3: Make source_id optional
ALTER TABLE documents 
ALTER COLUMN source_id DROP NOT NULL;

-- Step 4: Make blob_path optional
ALTER TABLE documents 
ALTER COLUMN blob_path DROP NOT NULL;

-- Step 5: Update user_id to UUID (if not already)
-- Note: This requires updating users, sources, documents, and document_chunks tables
DO $$
BEGIN
    -- Check if user_id is TEXT
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'documents' 
        AND column_name = 'user_id' 
        AND data_type = 'text'
    ) THEN
        -- Drop ALL RLS policies on all tables
        DROP POLICY IF EXISTS "Users can insert own documents" ON documents;
        DROP POLICY IF EXISTS "Users can view own documents" ON documents;
        DROP POLICY IF EXISTS "Users can update own documents" ON documents;
        DROP POLICY IF EXISTS "Users can delete own documents" ON documents;
        
        DROP POLICY IF EXISTS "Users can insert own sources" ON sources;
        DROP POLICY IF EXISTS "Users can view own sources" ON sources;
        DROP POLICY IF EXISTS "Users can update own sources" ON sources;
        DROP POLICY IF EXISTS "Users can delete own sources" ON sources;
        
        DROP POLICY IF EXISTS "Users can insert own chunks" ON document_chunks;
        DROP POLICY IF EXISTS "Users can view own chunks" ON document_chunks;
        DROP POLICY IF EXISTS "Users can update own chunks" ON document_chunks;
        DROP POLICY IF EXISTS "Users can delete own chunks" ON document_chunks;
        
        DROP POLICY IF EXISTS "Users can view own profile" ON users;
        DROP POLICY IF EXISTS "Users can update own profile" ON users;
        DROP POLICY IF EXISTS "Users can view own record" ON users;
        DROP POLICY IF EXISTS "Users can update own record" ON users;
        DROP POLICY IF EXISTS "Users can insert own record" ON users;
        DROP POLICY IF EXISTS "Users can delete own record" ON users;
        
        -- Drop ALL foreign key constraints
        ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_user_id_fkey;
        ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_source_id_fkey;
        ALTER TABLE sources DROP CONSTRAINT IF EXISTS sources_user_id_fkey;
        ALTER TABLE document_chunks DROP CONSTRAINT IF EXISTS document_chunks_user_id_fkey;
        ALTER TABLE document_chunks DROP CONSTRAINT IF EXISTS document_chunks_document_id_fkey;
        
        -- Update users.id to UUID first (no dependencies)
        ALTER TABLE users 
        ALTER COLUMN id TYPE UUID USING id::UUID;
        
        -- Update sources.user_id to UUID
        ALTER TABLE sources 
        ALTER COLUMN user_id TYPE UUID USING user_id::UUID;
        
        -- Update documents.user_id to UUID
        ALTER TABLE documents 
        ALTER COLUMN user_id TYPE UUID USING user_id::UUID;
        
        -- Update document_chunks.user_id to UUID
        ALTER TABLE document_chunks 
        ALTER COLUMN user_id TYPE UUID USING user_id::UUID;
        
        -- Recreate foreign key constraints
        ALTER TABLE sources
        ADD CONSTRAINT sources_user_id_fkey 
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
        
        ALTER TABLE documents
        ADD CONSTRAINT documents_user_id_fkey 
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
        
        ALTER TABLE documents
        ADD CONSTRAINT documents_source_id_fkey 
        FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE;
        
        ALTER TABLE document_chunks
        ADD CONSTRAINT document_chunks_user_id_fkey 
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
        
        ALTER TABLE document_chunks
        ADD CONSTRAINT document_chunks_document_id_fkey 
        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE;
        
        -- Recreate RLS policies on documents
        CREATE POLICY "Users can insert own documents"
            ON documents FOR INSERT
            WITH CHECK (auth.uid() = user_id);

        CREATE POLICY "Users can view own documents"
            ON documents FOR SELECT
            USING (auth.uid() = user_id);

        CREATE POLICY "Users can update own documents"
            ON documents FOR UPDATE
            USING (auth.uid() = user_id);

        CREATE POLICY "Users can delete own documents"
            ON documents FOR DELETE
            USING (auth.uid() = user_id);
        
        -- Recreate RLS policies on sources
        CREATE POLICY "Users can insert own sources"
            ON sources FOR INSERT
            WITH CHECK (auth.uid() = user_id);

        CREATE POLICY "Users can view own sources"
            ON sources FOR SELECT
            USING (auth.uid() = user_id);

        CREATE POLICY "Users can update own sources"
            ON sources FOR UPDATE
            USING (auth.uid() = user_id);

        CREATE POLICY "Users can delete own sources"
            ON sources FOR DELETE
            USING (auth.uid() = user_id);
        
        -- Recreate RLS policies on document_chunks
        CREATE POLICY "Users can insert own chunks"
            ON document_chunks FOR INSERT
            WITH CHECK (auth.uid() = user_id);

        CREATE POLICY "Users can view own chunks"
            ON document_chunks FOR SELECT
            USING (auth.uid() = user_id);

        CREATE POLICY "Users can update own chunks"
            ON document_chunks FOR UPDATE
            USING (auth.uid() = user_id);

        CREATE POLICY "Users can delete own chunks"
            ON document_chunks FOR DELETE
            USING (auth.uid() = user_id);
        
        -- Recreate RLS policies on users
        CREATE POLICY "Users can view own record"
            ON users FOR SELECT
            USING (auth.uid() = id);

        CREATE POLICY "Users can update own record"
            ON users FOR UPDATE
            USING (auth.uid() = id);
    END IF;
END $$;

-- Step 6: Drop token_count if it exists (not needed for now)
ALTER TABLE documents 
DROP COLUMN IF EXISTS token_count;

-- Step 7: Update index on content_hash (was hash)
DROP INDEX IF EXISTS idx_documents_hash;
CREATE INDEX idx_documents_content_hash ON documents(content_hash) WHERE content_hash IS NOT NULL;

-- Step 8: Add index on file_type for filtering
CREATE INDEX IF NOT EXISTS idx_documents_file_type ON documents(file_type);

-- Step 9: Add index on chunk_count for monitoring
CREATE INDEX IF NOT EXISTS idx_documents_chunk_count ON documents(chunk_count);

-- Step 10: Update RLS policies if needed
-- (RLS policies should continue to work since they filter on user_id)

-- Verification Query
-- Run this to check the schema after migration:
-- SELECT column_name, data_type, is_nullable
-- FROM information_schema.columns
-- WHERE table_name = 'documents'
-- ORDER BY ordinal_position;

COMMENT ON COLUMN documents.content_hash IS 'SHA256 hash of file content for deduplication';
COMMENT ON COLUMN documents.file_type IS 'File format: markdown, pdf, txt, etc.';
COMMENT ON COLUMN documents.file_size IS 'File size in bytes';
COMMENT ON COLUMN documents.chunk_count IS 'Number of chunks created from this document';
COMMENT ON COLUMN documents.metadata IS 'Flexible JSONB metadata (tags, categories, parser info)';
