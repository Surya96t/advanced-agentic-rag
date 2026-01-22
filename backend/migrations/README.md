# Database Migrations

This folder contains SQL migration files for the Integration Forge database.

---

## 📋 Migration Files

| Migration                          | Status            | Description                                              |
| ---------------------------------- | ----------------- | -------------------------------------------------------- |
| **001_initial_setup.sql**          | ✅ **APPLIED**    | Initial schema setup (extensions, tables, RLS, indexes)  |
| **002_update_document_schema.sql** | ⚠️ **SUPERSEDED** | Added document fields + UUID conversion (see note below) |
| **003_revert_user_id_to_text.sql** | ✅ **APPLIED**    | Reverted user_id to TEXT for Clerk compatibility         |

### ⚠️ Important Notes

**Migration History:**

- **001** created schema with TEXT user_id (Clerk-compatible)
- **002** changed user_id to UUID (broke Clerk integration) + added useful fields
- **003** reverted user_id back to TEXT (fixed Clerk compatibility)

**Current Schema State:**

- ✅ `users.id` is TEXT (Clerk user IDs like "user_2bXYZ123")
- ✅ All `user_id` foreign keys are TEXT
- ✅ Documents table has: `file_type`, `file_size`, `chunk_count`, `metadata`, `content_hash`
- ⚠️ RLS policies use `auth.uid()` (Supabase auth) - will be updated in Phase 6 for Clerk JWT

**Backend Compatibility:**

- Backend uses **service role key** which BYPASSES RLS
- Current setup works correctly for backend operations
- Phase 6 will implement proper Clerk JWT validation

---

## 🚀 How to Run Migrations

### **For New Setup (Fresh Database):**

Run migrations in order:

1. **001_initial_setup.sql** - Creates base schema
2. **002_update_document_schema.sql** - Adds document fields (includes UUID conversion)
3. **003_revert_user_id_to_text.sql** - Fixes Clerk compatibility

### **Already Applied All Migrations?**

✅ Your database is up to date! Current schema:

- 4 tables: users, sources, documents, document_chunks
- TEXT user_id throughout (Clerk-compatible)
- Document fields: file_type, file_size, chunk_count, metadata, content_hash
- HNSW vector index + GIN indexes
- RLS policies enabled (service role bypasses them)

---

## 📝 Running a Migration

### **Step 1: Open Supabase SQL Editor**

1. Go to your Supabase Dashboard: https://app.supabase.com
2. Select your project: `Integration Forge` (or your project name)
3. Click **SQL Editor** in the left sidebar

### **Step 2: Run the Migration**

1. Click **"New Query"** button
2. Open the migration file in your code editor (e.g., `001_initial_setup.sql`)
3. **Copy the ENTIRE file**
4. **Paste** into the Supabase SQL Editor
5. Click **"Run"** (or press `Cmd+Enter` / `Ctrl+Enter`)

### **Step 3: Verify Success**

Look for success messages in the output:

- ✅ "Success. No rows returned"
- ✅ Table/column/index created successfully

Or check manually:

1. Go to **Table Editor** in Supabase
2. Verify tables/columns exist

---

## 🔍 Current Database Schema

### **Tables:**

1. **users**
   - `id` TEXT PRIMARY KEY (Clerk user ID: "user_2bXYZ123")
   - `email` TEXT UNIQUE
   - `credits_used` INTEGER
   - `storage_bytes_used` BIGINT
   - `documents_count` INTEGER
   - Timestamps: `created_at`, `updated_at`

2. **sources**
   - `id` UUID PRIMARY KEY
   - `user_id` TEXT → users(id)
   - `name` TEXT
   - `description` TEXT
   - Timestamps: `created_at`, `updated_at`

3. **documents**
   - `id` UUID PRIMARY KEY
   - `source_id` UUID → sources(id) (nullable)
   - `user_id` TEXT → users(id)
   - `title` TEXT
   - `blob_path` TEXT (nullable)
   - `content_hash` TEXT (SHA256 hash for deduplication)
   - `file_type` TEXT (markdown, pdf, txt)
   - `file_size` INTEGER (bytes)
   - `chunk_count` INTEGER (processing progress)
   - `status` TEXT (pending, processing, completed, failed)
   - `metadata` JSONB (flexible metadata storage)
   - Timestamps: `created_at`, `updated_at`

4. **document_chunks**
   - `id` UUID PRIMARY KEY
   - `document_id` UUID → documents(id)
   - `user_id` TEXT → users(id)
   - `parent_chunk_id` UUID → document_chunks(id) (nullable)
   - `chunk_index` INTEGER (preserves document order)
   - `content` TEXT (the actual chunk text)
   - `metadata` JSONB (headers, page numbers, language, etc.)
   - `embedding` VECTOR(1536) (OpenAI text-embedding-3-small)
   - `chunk_type` TEXT (parent or child)
   - Timestamps: `created_at`, `updated_at`

### **Key Indexes:**

- **HNSW Vector Index:** `idx_chunks_embedding_hnsw` (fast semantic search)
- **GIN JSONB Index:** `idx_chunks_metadata` (metadata queries)
- **Foreign Key Indexes:** Document lookups, user filtering, parent-child navigation
- **Unique Indexes:** Email uniqueness, hash deduplication

### **Security:**

- ✅ RLS enabled on all tables
- ⚠️ Current policies use `auth.uid()` (Supabase auth syntax)
- ✅ Backend uses service role key (bypasses RLS)
- ⏳ Phase 6: Update policies for Clerk JWT validation

---

## 🧪 Verify Current Schema

Run this query in Supabase SQL Editor to confirm schema:

```sql
-- Check all user_id columns are TEXT
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

-- Expected output:
-- document_chunks | user_id | text         | NO
-- documents       | user_id | text         | NO
-- sources         | user_id | text         | NO
-- users           | id      | text         | NO
```

```sql
-- Check documents table columns (verify migration 002 fields)
SELECT
  column_name,
  data_type,
  is_nullable
FROM information_schema.columns
WHERE table_name = 'documents'
  AND table_schema = 'public'
ORDER BY ordinal_position;

-- Should include: content_hash, file_type, file_size, chunk_count, metadata
```

```sql
-- Test inserting a user (service role key required)
INSERT INTO users (id, email)
VALUES ('user_test_abc123', 'test@example.com')
RETURNING *;

-- Cleanup
DELETE FROM users WHERE id = 'user_test_abc123';
```

---

## 🔧 Troubleshooting

### **Problem: RLS policies blocking operations**

**Symptom:** `new row violates row-level security policy`

**Solution:**

- Backend should use **service role key** (bypasses RLS)
- Check `.env`: `SUPABASE_SERVICE_ROLE_KEY` is set correctly
- In `app/database/client.py`, verify using `settings.supabase_service_key`

### **Problem: Migration already applied**

**Symptom:** `relation "users" already exists`

**Solution:**

- Migrations 001-003 are idempotent where possible
- For 001: Use `DROP TABLE IF EXISTS` (destructive!)
- For 002-003: Use `IF EXISTS` / `IF NOT EXISTS` checks

### **Problem: Need to rollback migration 003**

**Not recommended!** Current schema is correct for Clerk.

If absolutely necessary:

```sql
-- Convert back to UUID (breaks Clerk integration!)
-- See migration 002 for the UUID conversion code
```

---

## 📚 Migration Details

For detailed information about each migration, see:

- **MIGRATION_GUIDE.md** - Comprehensive guide for all migrations
- Individual migration files for inline documentation

---

## 🚀 Next Steps

### **Phase 3: Retrieval System** (Current Focus)

- Will add `search_vector TSVECTOR` column (migration 004)
- Implements hybrid search (dense vector + sparse text)

### **Phase 6: Authentication & Security** (Future)

- Will update RLS policies for Clerk JWT validation
- Replace `auth.uid()` with JWT claims parsing

---

### **RLS (Row-Level Security):**

The migration enables RLS on all tables. This means:

- **Backend (service role):** Full access (bypasses RLS)
- **Frontend (anon/authenticated):** Filtered by user_id (RLS enforced)
- **Direct SQL queries:** Will fail unless using service role key

### **Vector Index Performance:**

The HNSW index has these parameters:

- `m = 16` - Connections per layer (good balance)
- `ef_construction = 64` - Build quality (good for < 1M vectors)
- Can be tuned later based on dataset size

---

## 🐛 Troubleshooting

### **Error: "extension 'vector' does not exist"**

**Solution:** Supabase projects created after 2023 have pgvector pre-installed. If you get this error:

1. Go to **Database → Extensions** in Supabase
2. Search for "vector"
3. Click "Enable"

### **Error: "permission denied for table..."**

**Solution:** Make sure you're using the **service_role** key in your backend `.env`, not the `anon` key.

### **Tables don't appear in Table Editor**

**Solution:**

1. Refresh the page
2. Check the SQL Editor output for errors
3. Try running the migration again (it's idempotent)

---

## 📚 Next Steps

After running this migration:

1. ✅ Verify tables exist in Supabase Table Editor
2. ✅ Update `PHASE2_TODO.md` - mark "Database setup" as complete
3. ✅ Continue with Python code (schemas, repositories, etc.)
