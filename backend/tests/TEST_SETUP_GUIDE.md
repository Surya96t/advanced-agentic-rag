# Test Setup Guide for Atomic Deletion

## Issues Found

Running `pytest tests/test_atomic_deletion.py` revealed two setup requirements:

### ❌ Issue 1: Migration Not Applied

```
'Could not find the function public.delete_document_with_chunks(doc_id) in the schema cache'
```

**Solution:** Apply migration 005 to create the RPC function.

### ❌ Issue 2: Foreign Key Constraint

```
'insert or update on table "documents" violates foreign key constraint "documents_user_id_fkey"'
Key (user_id)=(test_user_atomic_delete) is not present in table "users".
```

**Solution:** Create test user before running tests.

---

## Quick Fix: Apply Migration & Create Test User

### Step 1: Apply Migration 005

Open Supabase Dashboard → SQL Editor, then paste and run:

```sql
-- From: backend/migrations/005_add_delete_document_function.sql
-- (Copy the entire file contents)
```

Or use this quick version:

```bash
# Copy migration to clipboard
cat backend/migrations/005_add_delete_document_function.sql | pbcopy

# Then paste into Supabase SQL Editor and run
```

### Step 2: Create Test User

In Supabase SQL Editor, run:

```sql
-- Create test user for atomic deletion tests
INSERT INTO users (id, email, credits_used, storage_bytes_used, documents_count)
VALUES (
    'test_user_atomic_delete',
    'test_atomic@example.com',
    0,
    0,
    0
)
ON CONFLICT (id) DO NOTHING;
```

### Step 3: Re-run Tests

```bash
cd backend
uv run pytest tests/test_atomic_deletion.py -v
```

Expected: ✅ All tests pass!

---

## Better Solution: Add Test Fixtures

Update `tests/conftest.py` to auto-create test users for all tests.

This ensures tests are self-contained and don't require manual setup.

**Would you like me to:**

1. ✅ Update `conftest.py` with user creation fixtures?
2. ✅ Make the migration instructions clearer?
3. ✅ Create a test-only migration script?
