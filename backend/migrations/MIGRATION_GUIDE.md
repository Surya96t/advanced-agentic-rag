# Database Migration Guide

## Overview

This guide documents all database migrations for Integration Forge, including the evolution of the schema and important lessons learned.

---

## 📊 Migration History

| #   | File                             | Status        | Date         | Purpose                           |
| --- | -------------------------------- | ------------- | ------------ | --------------------------------- |
| 001 | `001_initial_setup.sql`          | ✅ Applied    | Jan 2026     | Initial schema with TEXT user_id  |
| 002 | `002_update_document_schema.sql` | ⚠️ Superseded | Jan 2026     | Document fields + UUID conversion |
| 003 | `003_revert_user_id_to_text.sql` | ✅ Applied    | Jan 21, 2026 | Clerk compatibility fix           |

---

## Migration 001: Initial Setup

### Purpose

Create the foundational database schema for the RAG system.

### What It Creates

**Extensions:**

- `uuid-ossp` - UUID generation
- `vector` - pgvector for embeddings

**Tables:**

- `users` - User accounts (id is TEXT for Clerk)
- `sources` - Document folders/collections
- `documents` - Uploaded files
- `document_chunks` - Text chunks with vector embeddings

**Indexes:**

- HNSW vector index on embeddings (cosine similarity)
- GIN index on JSONB metadata
- Foreign key indexes for performance

**RLS Policies:**

- Users can only see/modify their own data
- Uses `current_setting('request.jwt.claims', true)::json->>'sub'`

**Triggers:**

- Auto-update `updated_at` timestamps

**Functions:**

- `search_chunks_by_embedding()` - Vector similarity search

### Status

✅ **Applied and working correctly**

---

## Migration 002: Update Document Schema

### Purpose

Enhance the documents table to support the ingestion pipeline.

### Changes Made

1. ✅ **Renamed:** `hash` → `content_hash` (clearer naming)
2. ✅ **Added:** `file_type` TEXT (markdown, pdf, txt)
3. ✅ **Added:** `file_size` INTEGER (bytes)
4. ✅ **Added:** `chunk_count` INTEGER (processing progress tracking)
5. ✅ **Added:** `metadata` JSONB (flexible metadata storage)
6. ✅ **Made Optional:** `source_id`, `blob_path`
7. ⚠️ **Changed:** `user_id` from TEXT → UUID (broke Clerk integration!)
8. ✅ **Removed:** `token_count` column
9. ⚠️ **Updated RLS:** Changed to use `auth.uid()` (Supabase auth syntax)

### Issues Discovered

**Problem 1: UUID Conversion**

- Changed `users.id` and all `user_id` columns from TEXT to UUID
- Broke Clerk integration (Clerk uses string IDs like "user_2bXYZ123")
- Required migration 003 to fix

**Problem 2: RLS Policy Change**

- Changed from JWT claims parsing to `auth.uid()`
- Works with Supabase auth but not Clerk
- Will be addressed in Phase 6

### Status

⚠️ **Superseded by migration 003** (but beneficial changes retained)

---

## Migration 003: Revert user_id to TEXT (Clerk Compatibility)

### Purpose

Fix Clerk authentication compatibility by reverting user_id columns back to TEXT.

### What It Does

**Column Type Changes:**

1. `users.id` - UUID → TEXT
2. `sources.user_id` - UUID → TEXT
3. `documents.user_id` - UUID → TEXT
4. `document_chunks.user_id` - UUID → TEXT

**Process:**

1. Drops all RLS policies (they reference user_id)
2. Drops all foreign key constraints
3. Converts UUID columns to TEXT
4. Recreates foreign key constraints
5. Recreates RLS policies (using `auth.uid()::TEXT`)

**Safety:**

- Uses transaction (BEGIN/COMMIT)
- Preserves existing data during conversion
- Handles both fresh and existing databases

### Result

✅ **All user_id columns are now TEXT**

- Compatible with Clerk user IDs: "user_2bXYZ123"
- Foreign keys work correctly
- RLS policies active (but use Supabase auth syntax)

### Status

✅ **Applied successfully**

---

## 🎯 Current Schema State

After all migrations (001 → 002 → 003), your database has:

### **User ID Format:**

- ✅ TEXT throughout (Clerk-compatible)
- Format: "user_2bXYZ123" (Clerk)
- Not UUID

### **Documents Table:**

- ✅ Enhanced with migration 002 fields:
  - `content_hash` (was `hash`)
  - `file_type`, `file_size`, `chunk_count`
  - `metadata` JSONB
  - Optional `source_id` and `blob_path`
- ✅ TEXT user_id (migration 003)

### **All Tables:**

- ✅ RLS enabled
- ⚠️ Policies use `auth.uid()` (Supabase syntax)
- ✅ Backend bypasses RLS (service role key)

---

## 🚀 How to Apply Migrations

### For Fresh Database (Never Run Migrations)

Run in order:

```bash
# 1. Initial schema
# Open 001_initial_setup.sql in Supabase SQL Editor and run

# 2. Document enhancements + UUID conversion
# Open 002_update_document_schema.sql in Supabase SQL Editor and run

# 3. Clerk compatibility fix
# Open 003_revert_user_id_to_text.sql in Supabase SQL Editor and run
```

### Already Applied All Migrations?

✅ Nothing to do! Your schema is current.

---

## 🔧 Important Notes

### **Backend Uses Service Role Key**

Your backend (`app/database/client.py`) uses the service role key:

```python
cls._instance = create_client(
    supabase_url=settings.supabase_url,
    supabase_key=settings.supabase_service_key,  # Bypasses RLS!
)
```

**Implications:**

- ✅ Backend has full database access (no RLS filtering)
- ✅ Your code controls user_id filtering (explicit in queries)
- ✅ Current integration tests work correctly
- ⏳ Phase 6 will add Clerk JWT validation

### **RLS Policy Compatibility**

Current RLS policies use `auth.uid()` (Supabase auth function):

```sql
CREATE POLICY "Users can view own documents"
ON documents FOR SELECT
USING (auth.uid()::TEXT = user_id);
```

**For Clerk (Phase 6):**

- Will need to parse JWT claims manually
- Replace `auth.uid()` with `current_setting('request.jwt.claims', true)::json->>'sub'`
- Or use service role key + application-level authorization

---

## 🧪 Verification Queries

### Check User ID Types

```sql
-- Verify all user_id columns are TEXT
SELECT
  table_name,
  column_name,
  data_type,
  is_nullable
FROM information_schema.columns
WHERE column_name IN ('id', 'user_id')
  AND table_name IN ('users', 'sources', 'documents', 'document_chunks')
  AND table_schema = 'public'
ORDER BY table_name, column_name;
```

**Expected Output:**

```
table_name       | column_name | data_type | is_nullable
-----------------|-------------|-----------|-------------
document_chunks  | user_id     | text      | NO
documents        | user_id     | text      | NO
sources          | user_id     | text      | NO
users            | id          | text      | NO
```

### Check Documents Table Schema

```sql
-- Verify migration 002 fields exist
SELECT
  column_name,
  data_type,
  is_nullable,
  column_default
FROM information_schema.columns
WHERE table_name = 'documents'
  AND table_schema = 'public'
ORDER BY ordinal_position;
```

**Should Include:**

- `content_hash` TEXT (nullable)
- `file_type` TEXT (not null)
- `file_size` INTEGER (not null)
- `chunk_count` INTEGER (not null)
- `metadata` JSONB (not null)

### Test Data Operations

```sql
-- Test: Insert a Clerk-style user
INSERT INTO users (id, email)
VALUES ('user_test_abc123', 'test@example.com')
RETURNING *;

-- Test: Create a source
INSERT INTO sources (user_id, name, description)
VALUES ('user_test_abc123', 'Test Source', 'Integration test')
RETURNING *;

-- Test: Create a document with new fields
INSERT INTO documents (
  user_id,
  title,
  file_type,
  file_size,
  content_hash,
  status
)
VALUES (
  'user_test_abc123',
  'Test Document',
  'markdown',
  1024,
  'abc123hash',
  'pending'
)
RETURNING *;

-- Cleanup
DELETE FROM users WHERE id = 'user_test_abc123';
```

### Check RLS Policies

```sql
-- View all RLS policies
SELECT
  schemaname,
  tablename,
  policyname,
  permissive,
  cmd,
  qual
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;
```

**Note:** Policies should exist but use `auth.uid()` syntax.

---

## ⚠️ Known Issues & Future Work

### Issue 1: RLS Policies Use Supabase Auth Syntax

**Current State:**

```sql
USING (auth.uid()::TEXT = user_id)
```

**Needed for Clerk:**

```sql
USING (current_setting('request.jwt.claims', true)::json->>'sub' = user_id)
```

**When to Fix:** Phase 6 (Authentication & Security)

**Current Workaround:** Backend uses service role key (bypasses RLS)

### Issue 2: No Migration Versioning Table

**Current State:**

- No tracking of which migrations have been applied
- Manual verification required

**Future Improvement:**

- Create `schema_migrations` table
- Track migration number and timestamp
- Prevent accidental re-runs

---

## 🔄 Rollback Procedures

### Rollback Migration 003 (Not Recommended!)

⚠️ **Warning:** This breaks Clerk compatibility!

```sql
-- Follow migration 002 steps to convert back to UUID
-- Not recommended unless you're switching away from Clerk
```

### Rollback Migration 002

```sql
-- Rename back
ALTER TABLE documents RENAME COLUMN content_hash TO hash;

-- Remove new columns
ALTER TABLE documents
DROP COLUMN IF EXISTS file_type,
DROP COLUMN IF EXISTS file_size,
DROP COLUMN IF EXISTS chunk_count,
DROP COLUMN IF EXISTS metadata;

-- Make required again
ALTER TABLE documents
ALTER COLUMN source_id SET NOT NULL,
ALTER COLUMN blob_path SET NOT NULL;
```

### Rollback Migration 001 (Nuclear Option)

⚠️ **DESTROYS ALL DATA!**

```sql
DROP TABLE IF EXISTS document_chunks CASCADE;
DROP TABLE IF EXISTS documents CASCADE;
DROP TABLE IF EXISTS sources CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP EXTENSION IF EXISTS vector CASCADE;
DROP EXTENSION IF EXISTS "uuid-ossp" CASCADE;
```

---

## 📚 Migration Lessons Learned

### 1. **User ID Type Matters**

- Started with TEXT (correct for Clerk)
- Switched to UUID (broke Clerk)
- Reverted to TEXT (fixed)
- **Lesson:** Match your auth provider's ID format from the start

### 2. **RLS Policy Syntax Varies**

- Supabase auth: `auth.uid()`
- Clerk/Custom JWT: `current_setting('request.jwt.claims')::json->>'sub'`
- **Lesson:** Design RLS for your specific auth system

### 3. **Service Role Bypasses RLS**

- Backend with service role key doesn't use RLS
- Application handles authorization in code
- **Lesson:** RLS is optional if backend controls all access

### 4. **Migration Order Matters**

- 002 added fields (good) but changed user_id (bad)
- 003 fixed user_id but kept the good fields
- **Lesson:** Separate concerns in migrations

---

## 🚀 Next Migration: 004 (Planned)

```

### Purpose
Add full-text search capabilities for hybrid retrieval (Phase 3).

### Planned Changes

1. **Add Column:** `search_vector TSVECTOR` to `document_chunks`
2. **Add Trigger:** Auto-generate tsvector from content on INSERT/UPDATE
3. **Add Index:** GIN index on search_vector for fast text search
4. **Backfill:** Update existing chunks with search vectors

### When
During Phase 3: Retrieval System implementation

---

## 📞 Support

If you encounter migration issues:

1. Check verification queries above
2. Review migration file inline comments
3. Check Supabase dashboard for error messages
4. Verify service role key in `.env`
5. Consult README.md in this folder

---

## 📄 Related Files

- **README.md** - Quick reference and current schema state
- **001_initial_setup.sql** - Initial schema with detailed comments
- **002_update_document_schema.sql** - Document enhancements
- **003_revert_user_id_to_text.sql** - Clerk compatibility fix

---

**Last Updated:** January 22, 2026
**Schema Version:** 003 (TEXT user_id, enhanced documents)
**Next Migration:** 004 (Full-text search - Phase 3)
2. ✅ Verify documents can be ingested
3. ✅ Check chunks are stored correctly
4. ✅ Proceed to implement the API endpoint
```
