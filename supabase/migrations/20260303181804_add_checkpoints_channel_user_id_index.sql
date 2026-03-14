-- Migration: add_checkpoints_channel_user_id_index
-- Adds an index on the checkpoint JSONB channel_values user_id field
-- to support efficient per-user agent state queries.

CREATE INDEX IF NOT EXISTS idx_checkpoints_channel_user_id
    ON public.checkpoints USING btree
    (((checkpoint -> 'channel_values') ->> 'user_id'));
