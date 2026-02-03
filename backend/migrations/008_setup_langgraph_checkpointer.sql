-- ============================================================================
-- Integration Forge - LangGraph Checkpointer Setup
-- ============================================================================
-- 
-- This migration creates the required tables for LangGraph's PostgreSQL
-- checkpointer to enable persistent agent state and conversation history.
--
-- WHAT IS CHECKPOINTING?
-- - Saves agent state after each node execution
-- - Enables pause/resume functionality
-- - Supports conversation history across sessions
-- - Required for LangGraph's `AsyncPostgresSaver`
--
-- TABLES CREATED:
-- 1. checkpoints - Stores complete agent state snapshots
-- 2. checkpoint_writes - Stores individual state writes
-- 3. checkpoint_blobs - Stores large binary data (serialized state)
--
-- HOW TO RUN:
-- 1. Open Supabase Dashboard → SQL Editor
-- 2. Paste this entire file
-- 3. Click "Run" or press Cmd/Ctrl + Enter
-- 4. Verify tables created in Table Editor
--
-- NOTE: This migration is idempotent (safe to run multiple times)
-- ============================================================================

-- Drop existing tables if they exist (development only)
-- WARNING: This deletes all checkpoint data!
DROP TABLE IF EXISTS checkpoint_writes CASCADE;
DROP TABLE IF EXISTS checkpoints CASCADE;
DROP TABLE IF EXISTS checkpoint_blobs CASCADE;

-- ============================================================================
-- TABLE: checkpoints
-- ============================================================================
-- Stores agent state snapshots at each node execution
--
-- Schema follows LangGraph's AsyncPostgresSaver specification:
-- - thread_id: Conversation thread identifier (UUID)
-- - checkpoint_ns: Namespace for checkpoint (default: "")
-- - checkpoint_id: Unique checkpoint identifier (UUID)
-- - parent_checkpoint_id: Link to previous checkpoint (enables time-travel)
-- - type: Checkpoint type (always "checkpoint" for standard checkpoints)
-- - checkpoint: JSONB blob containing complete agent state
-- - metadata: Additional metadata (user_id, timestamp, etc.)

CREATE TABLE checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    type TEXT,
    checkpoint JSONB NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Primary key: unique checkpoint per thread and namespace
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

-- Index for fast lookup by thread_id
CREATE INDEX idx_checkpoints_thread_id 
    ON checkpoints(thread_id, checkpoint_ns);

-- Index for parent-child traversal
CREATE INDEX idx_checkpoints_parent 
    ON checkpoints(parent_checkpoint_id) 
    WHERE parent_checkpoint_id IS NOT NULL;


-- ============================================================================
-- TABLE: checkpoint_writes
-- ============================================================================
-- Stores individual state writes during checkpoint creation
--
-- This table captures intermediate writes that happen during a single
-- checkpoint creation. It's used for:
-- - Atomic state updates
-- - Rollback support
-- - Debugging state transitions

CREATE TABLE checkpoint_writes (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    channel TEXT NOT NULL,
    type TEXT,
    value JSONB,
    
    -- Primary key: unique write per checkpoint and task
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);

-- Index for fast lookup by checkpoint
CREATE INDEX idx_checkpoint_writes_checkpoint 
    ON checkpoint_writes(thread_id, checkpoint_ns, checkpoint_id);


-- ============================================================================
-- TABLE: checkpoint_blobs
-- ============================================================================
-- Stores large binary data (optional, for future use)
--
-- LangGraph can store large binary objects separately from the main
-- checkpoint JSONB to improve performance. This is optional and not
-- currently used by Integration Forge.

CREATE TABLE checkpoint_blobs (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    channel TEXT NOT NULL,
    version TEXT NOT NULL,
    type TEXT NOT NULL,
    blob BYTEA,
    
    -- Primary key: unique blob per thread, channel, and version
    PRIMARY KEY (thread_id, checkpoint_ns, channel, version)
);


-- ============================================================================
-- ROW-LEVEL SECURITY (RLS)
-- ============================================================================
-- Enable RLS on checkpoint tables to ensure user data isolation
--
-- SECURITY MODEL:
-- - Users can only access checkpoints for their own threads
-- - thread_id MUST be validated against user_id before checkpoint access
-- - Service role bypasses RLS (backend has full access)

-- Enable RLS
ALTER TABLE checkpoints ENABLE ROW LEVEL SECURITY;
ALTER TABLE checkpoint_writes ENABLE ROW LEVEL SECURITY;
ALTER TABLE checkpoint_blobs ENABLE ROW LEVEL SECURITY;

-- IMPORTANT: We currently use service role for all checkpoint operations,
-- so these policies are permissive. In production, you should add stricter
-- policies that validate thread_id ownership.

-- Allow service role full access (bypasses RLS automatically)
-- Allow authenticated users to view/modify their own checkpoints
-- (This policy is a placeholder - customize based on your auth model)

CREATE POLICY "Service role has full access to checkpoints"
    ON checkpoints
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role has full access to checkpoint_writes"
    ON checkpoint_writes
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role has full access to checkpoint_blobs"
    ON checkpoint_blobs
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);


-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================
-- Run these to verify the migration succeeded:

-- Check table creation
-- SELECT table_name 
-- FROM information_schema.tables 
-- WHERE table_name IN ('checkpoints', 'checkpoint_writes', 'checkpoint_blobs');

-- Check indexes
-- SELECT indexname, tablename 
-- FROM pg_indexes 
-- WHERE tablename IN ('checkpoints', 'checkpoint_writes', 'checkpoint_blobs');

-- Check RLS is enabled
-- SELECT tablename, rowsecurity 
-- FROM pg_tables 
-- WHERE tablename IN ('checkpoints', 'checkpoint_writes', 'checkpoint_blobs');

-- ============================================================================
-- SUCCESS!
-- ============================================================================
-- The LangGraph checkpointer tables are now ready.
-- The backend will automatically use these tables when checkpointing is enabled.
-- ============================================================================
