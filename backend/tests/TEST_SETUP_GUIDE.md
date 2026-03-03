# Test Setup Guide

## Overview

This guide covers manual setup steps required before running the integration test suites. Most test fixtures are self-contained — the only remaining manual step is applying the PostgreSQL RPC function to Supabase.

---

## `tests/test_atomic_deletion.py`

### ❌ Requires: `delete_document_with_chunks` RPC function

If the function has not been applied to Supabase, tests fail with:

```
'Could not find the function public.delete_document_with_chunks(doc_id) in the schema cache'
```

**Fix:** Open Supabase Dashboard → SQL Editor and run the following:

```sql
CREATE OR REPLACE FUNCTION delete_document_with_chunks(doc_id UUID)
RETURNS JSON AS $$
DECLARE
    v_document RECORD;
    v_chunks_deleted INTEGER;
BEGIN
    -- Verify document exists and get its metadata
    SELECT id, user_id, title INTO v_document
    FROM documents
    WHERE id = doc_id;

    IF NOT FOUND THEN
        RETURN json_build_object(
            'deleted', false,
            'error', 'Document not found'
        );
    END IF;

    -- Delete all chunks first (FK constraint)
    DELETE FROM document_chunks WHERE document_id = doc_id;
    GET DIAGNOSTICS v_chunks_deleted = ROW_COUNT;

    -- Delete the document
    DELETE FROM documents WHERE id = doc_id;

    RETURN json_build_object(
        'deleted', true,
        'document_id', doc_id,
        'chunks_deleted', v_chunks_deleted,
        'user_id', v_document.user_id,
        'title', v_document.title
    );
EXCEPTION WHEN OTHERS THEN
    -- PostgreSQL automatically rolls back the transaction on exception
    RETURN json_build_object(
        'deleted', false,
        'error', SQLERRM
    );
END;
$$ LANGUAGE plpgsql SECURITY INVOKER;
```

> **Note:** `SECURITY INVOKER` means the function runs with the caller's permissions. RLS policies on `documents` and `document_chunks` are still enforced — users can only delete their own records.

### ✅ Test user creation: handled automatically

The `test_user_id` fixture in `test_atomic_deletion.py` uses `upsert` to create the user before tests run:

```python
supabase.table("users").upsert({
    "id": user_id,
    "email": f"{user_id}@test.example.com",
    ...
}, on_conflict="id").execute()
```

No manual user creation required.

### Run

```bash
cd backend
uv run pytest tests/test_atomic_deletion.py -v
```

---

## `tests/test_sse_streaming.py`

### ✅ No manual setup required — 8/8 tests pass

Auth is bypassed via `dependency_overrides` in the `async_client` fixture:

```python
app.dependency_overrides[get_current_user_id] = lambda: "test_user_id"
app.dependency_overrides[check_user_rate_limit] = lambda: None
```

The endpoint code uses `getattr(request.app.state, "checkpointer", None)` so it degrades gracefully when the ASGI test transport doesn't run the lifespan (i.e., no real checkpointer is instantiated).

```bash
cd backend
uv run pytest tests/test_sse_streaming.py -v
```

---

## `tests/test_authentication.py`

### ⚠️ Requires: Redis

Rate limiting tests depend on a running Redis instance. Without it, tests that exercise rate limit enforcement will fail.

```bash
# Start Redis locally
redis-server

# Then run
cd backend
uv run pytest tests/test_authentication.py -v
```

---

## `tests/test_agent_integration.py` / `tests/test_retrieval_integration.py`

### ⚠️ Requires: Live Supabase + OpenAI credentials

These tests call real external services and take 2–3 minutes per test. Ensure `.env` in `backend/` has valid values for:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `OPENAI_API_KEY`

Test data must also be ingested first:

```bash
cd backend
uv run scripts/ingest_test_data.py
uv run pytest tests/test_agent_integration.py tests/test_retrieval_integration.py -v
```
