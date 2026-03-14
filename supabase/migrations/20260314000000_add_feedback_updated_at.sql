-- Migration: add_feedback_updated_at
-- Adds updated_at column to feedback table to match FeedbackResponse schema.

ALTER TABLE public.feedback
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NULL;
