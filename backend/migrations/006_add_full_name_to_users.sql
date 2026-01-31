-- ============================================================================
-- Migration: Add full_name column to users table
-- ============================================================================
-- 
-- This migration adds the full_name column to store user's display name from Clerk.
-- This is safe to run multiple times (idempotent).
--
-- HOW TO RUN:
-- 1. Open Supabase Dashboard → SQL Editor
-- 2. Paste this file
-- 3. Click "Run" or press Cmd/Ctrl + Enter
-- ============================================================================

-- Add full_name column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'users' 
        AND column_name = 'full_name'
    ) THEN
        ALTER TABLE users ADD COLUMN full_name TEXT;
    END IF;
END $$;

-- Add comment for documentation
COMMENT ON COLUMN users.full_name IS 'User''s full name from Clerk authentication';
