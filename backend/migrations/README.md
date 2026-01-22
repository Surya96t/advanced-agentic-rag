# Database Migrations

This folder contains SQL migration files for the Integration Forge database.

---

## 📋 Migration Files

- **`001_initial_setup.sql`** - Initial schema setup (extensions, tables, RLS, indexes)

---

## 🚀 How to Run Migrations

### **Step 1: Open Supabase SQL Editor**

1. Go to your Supabase Dashboard: https://app.supabase.com
2. Select your project: `Integration Forge` (or your project name)
3. Click **SQL Editor** in the left sidebar

### **Step 2: Run the Migration**

1. Click **"New Query"** button
2. Open `001_initial_setup.sql` in your code editor
3. **Copy the ENTIRE file** (all ~500 lines)
4. **Paste** into the Supabase SQL Editor
5. Click **"Run"** (or press `Cmd+Enter` / `Ctrl+Enter`)

### **Step 3: Verify Success**

Look for these messages in the output:

- ✅ "Success. No rows returned"
- ✅ Table list showing: `users`, `sources`, `documents`, `document_chunks`

Or check manually:

1. Go to **Table Editor** in Supabase
2. You should see 4 tables listed

### **Step 4: Test the Schema**

Run this query to verify everything works:

```sql
-- Test: Insert a test user
INSERT INTO users (id, email)
VALUES ('user_test123', 'test@example.com')
RETURNING *;

-- Test: Create a source
INSERT INTO sources (user_id, name, description)
VALUES ('user_test123', 'Test Source', 'Testing the schema')
RETURNING *;

-- Cleanup
DELETE FROM users WHERE id = 'user_test123';
```

---

## 🔍 Understanding the Migration

### **What Gets Created:**

1. **Extensions:**
   - `uuid-ossp` - UUID generation
   - `vector` - pgvector for embeddings

2. **Tables:**
   - `users` - User accounts
   - `sources` - Document folders
   - `documents` - Uploaded files
   - `document_chunks` - Text chunks with embeddings

3. **Indexes:**
   - Foreign key indexes (performance)
   - HNSW vector index (fast similarity search)
   - GIN JSONB index (metadata queries)

4. **RLS Policies:**
   - Users can only see their own data
   - Service role bypasses RLS (backend access)

5. **Triggers:**
   - Auto-update `updated_at` timestamps

6. **Functions:**
   - `search_chunks_by_embedding()` - Vector similarity search

---

## ⚠️ Important Notes

### **Development vs Production:**

- This migration uses `DROP TABLE IF EXISTS CASCADE`
- **Safe for initial setup** (no data loss because tables don't exist yet)
- **Dangerous if re-run later** (would delete all data!)
- In production, use `ALTER TABLE` for schema changes

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
