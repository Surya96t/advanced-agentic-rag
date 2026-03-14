-- Migration: create_rag_evaluations
-- Creates the rag_evaluations table for storing Ragas evaluation results
-- against the CUAD ground truth dataset.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS public.rag_evaluations (
    id                  UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_name            TEXT            NOT NULL,
    chunking_strategy   TEXT            NOT NULL,
    model               TEXT            NOT NULL,
    question            TEXT            NOT NULL,
    ground_truth        TEXT            NOT NULL,
    generated_answer    TEXT            NOT NULL,
    retrieved_chunks    JSONB           NOT NULL DEFAULT '[]',
    -- Ragas metrics (nullable: filled after evaluation completes)
    context_precision   DOUBLE PRECISION,
    context_recall      DOUBLE PRECISION,
    faithfulness        DOUBLE PRECISION,
    answer_relevancy    DOUBLE PRECISION,
    ragas_score         DOUBLE PRECISION,
    -- Performance
    latency_ms          INTEGER,
    -- Source tracking
    contract_filename   TEXT,
    created_at          TIMESTAMPTZ     DEFAULT now()
);

-- Index for querying by run
CREATE INDEX IF NOT EXISTS idx_rag_evaluations_run_name
    ON public.rag_evaluations (run_name);

-- Index for querying by chunking strategy
CREATE INDEX IF NOT EXISTS idx_rag_evaluations_chunking_strategy
    ON public.rag_evaluations (chunking_strategy);
