-- Migration: add_checkpoints_user_id_index
-- Adds indexes on the checkpoints table to enable efficient per-user
-- conversation history lookups without full-table scans.

CREATE INDEX IF NOT EXISTS idx_checkpoints_user_id
    ON public.checkpoints USING btree ((metadata ->> 'user_id'));

CREATE INDEX IF NOT EXISTS idx_checkpoints_user_ns
    ON public.checkpoints USING btree ((metadata ->> 'user_id'), checkpoint_ns);
