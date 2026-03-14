-- Migration: create_storage_documents_bucket
-- Creates the private Supabase Storage bucket for user-uploaded documents
-- and establishes per-user RLS policies (folder = uid).

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'documents',
    'documents',
    false,
    52428800,  -- 50 MB
    ARRAY[
        'application/pdf',
        'text/plain',
        'text/markdown',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ]
)
ON CONFLICT (id) DO NOTHING;

-- RLS: Users can only access objects under their own uid folder
CREATE POLICY "Users can upload own files"
    ON storage.objects FOR INSERT
    WITH CHECK (
        bucket_id = 'documents'
        AND (storage.foldername(name))[1] = (auth.uid())::text
    );

CREATE POLICY "Users can view own files"
    ON storage.objects FOR SELECT
    USING (
        bucket_id = 'documents'
        AND (storage.foldername(name))[1] = (auth.uid())::text
    );

CREATE POLICY "Users can delete own files"
    ON storage.objects FOR DELETE
    USING (
        bucket_id = 'documents'
        AND (storage.foldername(name))[1] = (auth.uid())::text
    );
