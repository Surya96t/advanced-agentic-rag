-- Migration: enterprise_contracts_bucket
-- Creates a private Supabase Storage bucket for enterprise CUAD contract files.
-- Access is restricted to authenticated users (service role uploads only).

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'enterprise-contracts',
    'enterprise-contracts',
    false,
    52428800,  -- 50 MB
    ARRAY[
        'text/plain',
        'application/pdf',
        'text/markdown'
    ]
)
ON CONFLICT (id) DO NOTHING;
