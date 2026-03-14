-- Migration: enterprise_two_tier_rls
-- Updates RLS policies on documents and document_chunks to support a
-- two-tier access model:
--   1. Personal: user_id = auth.uid()
--   2. Enterprise shared corpus: user_id = 'system'
--
-- This allows enterprise-wide shared documents (ingested with user_id='system')
-- to be visible to all authenticated users, while personal documents remain private.

-- ─── documents ───────────────────────────────────────────────────────────────

DROP POLICY IF EXISTS "Users can view own documents" ON public.documents;
CREATE POLICY "Users can view own and enterprise documents"
    ON public.documents FOR SELECT
    USING (user_id = (auth.uid())::text OR user_id = 'system');

DROP POLICY IF EXISTS "Users can insert own documents" ON public.documents;
CREATE POLICY "Users can insert own documents"
    ON public.documents FOR INSERT
    WITH CHECK (user_id = (auth.uid())::text);

DROP POLICY IF EXISTS "Users can update own documents" ON public.documents;
CREATE POLICY "Users can update own documents"
    ON public.documents FOR UPDATE
    USING (user_id = (auth.uid())::text);

DROP POLICY IF EXISTS "Users can delete own documents" ON public.documents;
CREATE POLICY "Users can delete own documents"
    ON public.documents FOR DELETE
    USING (user_id = (auth.uid())::text);

-- ─── document_chunks ───────────────────────────────────────────────────────

DROP POLICY IF EXISTS "Users can view own chunks" ON public.document_chunks;
CREATE POLICY "Users can view own and enterprise chunks"
    ON public.document_chunks FOR SELECT
    USING (user_id = (auth.uid())::text OR user_id = 'system');

DROP POLICY IF EXISTS "Users can insert own chunks" ON public.document_chunks;
CREATE POLICY "Users can insert own chunks"
    ON public.document_chunks FOR INSERT
    WITH CHECK (user_id = (auth.uid())::text OR user_id = 'system');

DROP POLICY IF EXISTS "Users can update own chunks" ON public.document_chunks;
CREATE POLICY "Users can update own chunks"
    ON public.document_chunks FOR UPDATE
    USING (user_id = (auth.uid())::text OR user_id = 'system');

DROP POLICY IF EXISTS "Users can delete own chunks" ON public.document_chunks;
CREATE POLICY "Users can delete own chunks"
    ON public.document_chunks FOR DELETE
    USING (user_id = (auth.uid())::text OR user_id = 'system');
