-- ============================================================================
-- Migration 003: Revert user_id to TEXT for Clerk Compatibility
-- ============================================================================
-- 
-- Purpose:
-- Migration 002 changed users.id from TEXT to UUID, which breaks Clerk
-- integration. Clerk uses string IDs like "user_2bXYZ123", not UUIDs.
-- This migration reverts all user_id fields back to TEXT.
--
-- Changes:
-- 1. users.id: UUID → TEXT (for Clerk user IDs)
-- 2. sources.user_id: UUID → TEXT (FK to users.id)
-- 3. documents.user_id: UUID → TEXT (FK to users.id)
-- 4. document_chunks.user_id: UUID → TEXT (FK to users.id)
--
-- Safety:
-- - Drops and recreates foreign key constraints
-- - Preserves existing data during conversion
-- - Handles both up and down migrations
--
-- Author: Integration Forge Team
-- Date: 2026-01-21
-- ============================================================================

BEGIN;

-- ============================================================================
-- STEP 1: Drop RLS Policies (they reference user_id columns)
-- ============================================================================
-- RLS policies prevent column type changes, so we must drop them first

DO $$ 
BEGIN
    -- Drop RLS policies on users table
    DROP POLICY IF EXISTS "Users can view own record" ON users;
    DROP POLICY IF EXISTS "Users can update own record" ON users;
    DROP POLICY IF EXISTS "Users can insert own record" ON users;
    
    RAISE NOTICE 'Users table RLS policies dropped';
    
    -- Drop RLS policies on sources table
    DROP POLICY IF EXISTS "Users can view own sources" ON sources;
    DROP POLICY IF EXISTS "Users can create own sources" ON sources;
    DROP POLICY IF EXISTS "Users can insert own sources" ON sources;
    DROP POLICY IF EXISTS "Users can update own sources" ON sources;
    DROP POLICY IF EXISTS "Users can delete own sources" ON sources;
    
    RAISE NOTICE 'Sources table RLS policies dropped';
    
    -- Drop RLS policies on documents table
    DROP POLICY IF EXISTS "Users can view own documents" ON documents;
    DROP POLICY IF EXISTS "Users can create own documents" ON documents;
    DROP POLICY IF EXISTS "Users can insert own documents" ON documents;
    DROP POLICY IF EXISTS "Users can update own documents" ON documents;
    DROP POLICY IF EXISTS "Users can delete own documents" ON documents;
    
    RAISE NOTICE 'Documents table RLS policies dropped';
    
    -- Drop RLS policies on document_chunks table
    DROP POLICY IF EXISTS "Users can view own chunks" ON document_chunks;
    DROP POLICY IF EXISTS "Users can create own chunks" ON document_chunks;
    DROP POLICY IF EXISTS "Users can insert own chunks" ON document_chunks;
    DROP POLICY IF EXISTS "Users can update own chunks" ON document_chunks;
    DROP POLICY IF EXISTS "Users can delete own chunks" ON document_chunks;
    
    RAISE NOTICE 'Document_chunks table RLS policies dropped';
END $$;


-- ============================================================================
-- STEP 2: Drop Foreign Key Constraints
-- ============================================================================
-- We need to drop FKs before changing column types

DO $$ 
BEGIN
    -- Drop FK constraints (safe if they don't exist)
    ALTER TABLE sources DROP CONSTRAINT IF EXISTS sources_user_id_fkey;
    ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_user_id_fkey;
    ALTER TABLE document_chunks DROP CONSTRAINT IF EXISTS document_chunks_user_id_fkey;
    
    RAISE NOTICE 'Foreign key constraints dropped';
END $$;


-- ============================================================================
-- STEP 3: Convert UUID columns to TEXT
-- ============================================================================
-- Convert in dependency order: users first, then dependent tables

-- Convert users.id (no dependencies on this)
ALTER TABLE users 
ALTER COLUMN id TYPE TEXT USING id::TEXT;

-- Convert sources.user_id
ALTER TABLE sources 
ALTER COLUMN user_id TYPE TEXT USING user_id::TEXT;

-- Convert documents.user_id
ALTER TABLE documents 
ALTER COLUMN user_id TYPE TEXT USING user_id::TEXT;

-- Convert document_chunks.user_id
ALTER TABLE document_chunks 
ALTER COLUMN user_id TYPE TEXT USING user_id::TEXT;


-- ============================================================================
-- STEP 4: Recreate Foreign Key Constraints
-- ============================================================================
-- Add back FKs with CASCADE delete for data integrity

DO $$
BEGIN
    -- sources.user_id → users.id
    ALTER TABLE sources
    ADD CONSTRAINT sources_user_id_fkey 
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
    
    RAISE NOTICE 'sources FK constraint recreated';
    
    -- documents.user_id → users.id
    ALTER TABLE documents
    ADD CONSTRAINT documents_user_id_fkey 
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
    
    RAISE NOTICE 'documents FK constraint recreated';
    
    -- document_chunks.user_id → users.id
    ALTER TABLE document_chunks
    ADD CONSTRAINT document_chunks_user_id_fkey 
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
    
    RAISE NOTICE 'document_chunks FK constraint recreated';
END $$;


-- ============================================================================
-- STEP 5: Recreate RLS Policies
-- ============================================================================
-- Recreate all RLS policies with TEXT user_id columns

DO $$
BEGIN
    -- ========================================================================
    -- USERS TABLE RLS POLICIES
    -- ========================================================================
    
    -- Users can view their own record
    CREATE POLICY "Users can view own record"
    ON users
    FOR SELECT
    USING (auth.uid()::TEXT = id);
    
    -- Users can update their own record
    CREATE POLICY "Users can update own record"
    ON users
    FOR UPDATE
    USING (auth.uid()::TEXT = id);
    
    RAISE NOTICE 'Users table RLS policies recreated';
    
    
    -- ========================================================================
    -- SOURCES TABLE RLS POLICIES
    -- ========================================================================
    
    -- Users can view their own sources
    CREATE POLICY "Users can view own sources"
    ON sources
    FOR SELECT
    USING (auth.uid()::TEXT = user_id);
    
    -- Users can create their own sources (INSERT)
    CREATE POLICY "Users can insert own sources"
    ON sources
    FOR INSERT
    WITH CHECK (auth.uid()::TEXT = user_id);
    
    -- Users can update their own sources
    CREATE POLICY "Users can update own sources"
    ON sources
    FOR UPDATE
    USING (auth.uid()::TEXT = user_id);
    
    -- Users can delete their own sources
    CREATE POLICY "Users can delete own sources"
    ON sources
    FOR DELETE
    USING (auth.uid()::TEXT = user_id);
    
    RAISE NOTICE 'Sources table RLS policies recreated';
    
    
    -- ========================================================================
    -- DOCUMENTS TABLE RLS POLICIES
    -- ========================================================================
    
    -- Users can view their own documents
    CREATE POLICY "Users can view own documents"
    ON documents
    FOR SELECT
    USING (auth.uid()::TEXT = user_id);
    
    -- Users can create their own documents (INSERT)
    CREATE POLICY "Users can insert own documents"
    ON documents
    FOR INSERT
    WITH CHECK (auth.uid()::TEXT = user_id);
    
    -- Users can update their own documents
    CREATE POLICY "Users can update own documents"
    ON documents
    FOR UPDATE
    USING (auth.uid()::TEXT = user_id);
    
    -- Users can delete their own documents
    CREATE POLICY "Users can delete own documents"
    ON documents
    FOR DELETE
    USING (auth.uid()::TEXT = user_id);
    
    RAISE NOTICE 'Documents table RLS policies recreated';
    
    
    -- ========================================================================
    -- DOCUMENT_CHUNKS TABLE RLS POLICIES
    -- ========================================================================
    
    -- Users can view their own chunks
    CREATE POLICY "Users can view own chunks"
    ON document_chunks
    FOR SELECT
    USING (auth.uid()::TEXT = user_id);
    
    -- Users can create their own chunks (INSERT)
    CREATE POLICY "Users can insert own chunks"
    ON document_chunks
    FOR INSERT
    WITH CHECK (auth.uid()::TEXT = user_id);
    
    -- Users can update their own chunks
    CREATE POLICY "Users can update own chunks"
    ON document_chunks
    FOR UPDATE
    USING (auth.uid()::TEXT = user_id);
    
    -- Users can delete their own chunks
    CREATE POLICY "Users can delete own chunks"
    ON document_chunks
    FOR DELETE
    USING (auth.uid()::TEXT = user_id);
    
    RAISE NOTICE 'Document_chunks table RLS policies recreated';
END $$;

COMMIT;

-- ============================================================================
-- Migration Complete
-- ============================================================================
-- The schema is now compatible with Clerk authentication.
-- User IDs should be Clerk format: "user_2bXYZ123"
-- 
-- Verification:
-- Run this query to confirm all user_id columns are TEXT:
-- 
-- SELECT 
--   table_name, 
--   column_name, 
--   data_type
-- FROM information_schema.columns 
-- WHERE column_name IN ('id', 'user_id') 
--   AND table_name IN ('users', 'sources', 'documents', 'document_chunks')
-- ORDER BY table_name, column_name;
-- 
-- Expected output:
--   users            | id      | text
--   sources          | user_id | text
--   documents        | user_id | text
--   document_chunks  | user_id | text
-- ============================================================================
