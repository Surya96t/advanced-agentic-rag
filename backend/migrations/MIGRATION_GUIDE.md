# Database Migration Guide

## Migration 002: Update Document Schema

This migration updates the `documents` table to align with the ingestion pipeline requirements.

### What Changed

- ✅ **Renamed:** `hash` → `content_hash` (clearer naming)
- ✅ **Added:** `file_type` (markdown, pdf, txt)
- ✅ **Added:** `file_size` (bytes)
- ✅ **Added:** `chunk_count` (processing progress)
- ✅ **Added:** `metadata` (JSONB for flexible data)
- ✅ **Made Optional:** `source_id`, `blob_path`
- ✅ **Updated:** `user_id` from TEXT to UUID
- ✅ **Removed:** `token_count` (not needed yet)

### How to Run

#### Option 1: Supabase Dashboard (Recommended)

1. Go to https://supabase.com/dashboard
2. Select your project
3. Click "SQL Editor" in the left sidebar
4. Click "New query"
5. Copy the entire contents of `migrations/002_update_document_schema.sql`
6. Paste into the SQL editor
7. Click "Run" (or press Cmd/Ctrl + Enter)
8. Verify success message

#### Option 2: Supabase CLI

```bash
# Make sure you're in the backend directory
cd backend

# Run the migration
supabase db push --include-all

# Or use psql directly
psql $DATABASE_URL -f migrations/002_update_document_schema.sql
```

### Verify Migration

After running, verify the schema:

```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'documents'
ORDER BY ordinal_position;
```

Expected columns:

- `id` (uuid, not null)
- `user_id` (uuid, not null)
- `title` (text, not null)
- `file_type` (text, not null)
- `file_size` (integer, not null)
- `content_hash` (text, nullable)
- `chunk_count` (integer, not null)
- `status` (text, not null)
- `source_id` (uuid, nullable)
- `blob_path` (text, nullable)
- `metadata` (jsonb, not null)
- `created_at` (timestamp, not null)
- `updated_at` (timestamp, not null)

### Rollback (if needed)

If you need to rollback this migration:

```sql
-- Rename back
ALTER TABLE documents RENAME COLUMN content_hash TO hash;

-- Remove new columns
ALTER TABLE documents
DROP COLUMN file_type,
DROP COLUMN file_size,
DROP COLUMN chunk_count,
DROP COLUMN metadata;

-- Make required again
ALTER TABLE documents
ALTER COLUMN source_id SET NOT NULL,
ALTER COLUMN blob_path SET NOT NULL;

-- Add back token_count
ALTER TABLE documents
ADD COLUMN token_count INTEGER NOT NULL DEFAULT 0;
```

### Next Steps

After running this migration:

1. ✅ Run the integration test: `python tests/test_ingestion_pipeline_integration.py`
2. ✅ Verify documents can be ingested
3. ✅ Check chunks are stored correctly
4. ✅ Proceed to implement the API endpoint
