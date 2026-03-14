-- Migration: add_feedback_updated_at
-- Adds updated_at column to feedback table to match FeedbackResponse schema.
-- Backfills existing rows, sets a default, and wires an auto-update trigger.

-- 1. Add column (idempotent)
ALTER TABLE public.feedback
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NULL;

-- 2. Backfill existing rows (use created_at as a sensible baseline)
UPDATE public.feedback SET updated_at = created_at WHERE updated_at IS NULL;

-- 3. Set default so new inserts automatically get a timestamp
ALTER TABLE public.feedback
    ALTER COLUMN updated_at SET DEFAULT now();

-- 4. Trigger function (idempotent via CREATE OR REPLACE)
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

-- 5. Trigger on feedback (drop first for idempotency)
DROP TRIGGER IF EXISTS trg_feedback_updated_at ON public.feedback;
CREATE TRIGGER trg_feedback_updated_at
    BEFORE UPDATE ON public.feedback
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();
