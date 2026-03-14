-- Migration: create_feedback_table
-- Creates the feedback table for storing user message ratings.

CREATE TABLE IF NOT EXISTS public.feedback (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      TEXT        NOT NULL,
    feedback_type TEXT       NOT NULL,
    message      TEXT        NOT NULL,
    rating       INTEGER     NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Enable Row-Level Security
ALTER TABLE public.feedback ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can insert own feedback"
    ON public.feedback FOR INSERT
    WITH CHECK (user_id = (auth.uid())::text);

CREATE POLICY "Users can view own feedback"
    ON public.feedback FOR SELECT
    USING (user_id = (auth.uid())::text);
