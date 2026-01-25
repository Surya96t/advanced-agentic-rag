# Atomic Document Deletion Implementation

**Date:** 2026-01-24  
**Phase:** 5 (API Endpoints)  
**Status:** ✅ Implemented

---

## Overview

Implemented true ACID-compliant atomic deletion of documents and their chunks using PostgreSQL stored procedures (RPC). This ensures all-or-nothing behavior with no possibility of orphaned chunks or partial deletions.

---

## Problem Statement

**Before:** Client-side deletion strategy had atomicity issues:

- Chunks deleted first, then document
- If document deletion failed, orphaned chunks remained
- Try/except compensating strategy logged errors but couldn't rollback
- Required manual cleanup for partial failures

**After:** PostgreSQL RPC provides true transaction support:

- ✅ Both deletes in single transaction
- ✅ Automatic rollback on any failure
- ✅ No orphaned chunks possible
- ✅ Better performance (single round-trip)

---

## Implementation Details

### 1. PostgreSQL Stored Procedure

**File:** `backend/migrations/005_add_delete_document_function.sql`

**Function Signature:**

```sql
delete_document_with_chunks(doc_id UUID) RETURNS JSON
```

**Transaction Behavior:**

1. BEGIN (implicit)
2. Verify document exists and get metadata
3. DELETE all chunks for document
4. DELETE document record
5. COMMIT if all succeed, ROLLBACK on any error

**Security:**

- `SECURITY INVOKER` - runs with caller's permissions
- RLS policies automatically enforced
- Only document owner can delete (via RLS)

**Returns:**

```json
{
  "deleted": true,
  "document_id": "uuid",
  "chunks_deleted": 42,
  "user_id": "test_user_123",
  "title": "Document Title"
}
```

---

### 2. Repository Method

**File:** `backend/app/database/repositories/documents.py`

**New Method:** `delete_with_chunks(document_id: UUID, user_id: str) -> dict`

**Features:**

- Calls PostgreSQL RPC via `supabase.rpc()`
- Validates response and raises appropriate errors
- Comprehensive logging and error handling
- Returns deletion statistics

**Error Handling:**

- `NotFoundError` if document doesn't exist or user doesn't own it
- `DatabaseError` if RPC call fails
- Automatic transaction rollback by PostgreSQL

---

### 3. API Endpoint Update

**File:** `backend/app/api/v1/documents.py`

**Changes:**

- Removed compensating strategy (try/except blocks)
- Removed `ChunkRepository` import (no longer needed)
- Replaced client-side deletion with single RPC call
- Simplified error handling (PostgreSQL manages atomicity)

**Code Comparison:**

**Before (70+ lines):**

```python
chunks_deleted = 0
document_deleted = False

try:
    chunks_deleted = chunk_repo.delete_by_document(document_id)
    doc_repo.delete(document_id)
    document_deleted = True
    # ... logging and response
except Exception as delete_error:
    # ... complex error handling and partial state logging
    raise HTTPException(...)
```

**After (10 lines):**

```python
result = doc_repo.delete_with_chunks(document_id, user_id)

logger.info("Document deleted successfully (atomic)", ...)

return DocumentDeleteResponse(
    deleted=True,
    document_id=document_id,
    chunks_deleted=result.get("chunks_deleted", 0)
)
```

---

### 4. Test Suite

**File:** `backend/tests/test_atomic_deletion.py`

**Test Coverage:**

- ✅ Successful atomic deletion
- ✅ Delete nonexistent document (NotFoundError)
- ✅ Delete document without chunks (edge case)
- ✅ RLS enforcement (different user cannot delete)
- ✅ Parent-child chunk hierarchies
- ✅ Idempotent deletion (double-delete)
- ✅ Performance with large chunk counts (100+ chunks)

**Manual Testing Guide:**

- Instructions for simulating rollback scenarios
- How to verify transaction atomicity in SQL Editor
- Expected behavior documentation

---

## Benefits

### **Correctness**

- ✅ True ACID compliance (Atomicity, Consistency, Isolation, Durability)
- ✅ No orphaned chunks ever
- ✅ Automatic rollback on failures
- ✅ Consistent state guaranteed

### **Performance**

- ✅ Single database round-trip (was 2+ queries)
- ✅ No N+1 queries for chunks
- ✅ Faster execution (PostgreSQL-native)
- ✅ Reduced network latency

### **Security**

- ✅ RLS enforced at database layer
- ✅ Cannot bypass ownership checks
- ✅ Consistent with Supabase's own functions
- ✅ Function runs with caller's permissions

### **Maintainability**

- ✅ Simpler API endpoint code (70 lines → 10 lines)
- ✅ No complex compensating logic
- ✅ Easier to test and reason about
- ✅ Self-documenting SQL with comments

---

## Migration Guide

### **Step 1: Run Migration**

```bash
# Open Supabase Dashboard → SQL Editor
# Copy contents of: backend/migrations/005_add_delete_document_function.sql
# Paste and execute
```

**Expected Output:**

```
NOTICE: Created delete_document_with_chunks() function with RLS enforcement
NOTICE: Usage: SELECT * FROM delete_document_with_chunks('uuid-here')
```

### **Step 2: Verify Function**

```sql
-- Test with a real document ID
SELECT * FROM delete_document_with_chunks('your-document-uuid');

-- Expected result:
-- {"deleted": true, "chunks_deleted": N, ...}
```

### **Step 3: Test API Endpoint**

```bash
# Delete a document via API
curl -X DELETE http://localhost:8000/api/v1/documents/{document_id}

# Expected: 200 OK with deletion stats
# Verify in database: document and chunks gone
```

### **Step 4: Run Test Suite**

```bash
cd backend
pytest tests/test_atomic_deletion.py -v

# All tests should pass
```

---

## Rollback Plan (If Needed)

If issues arise, you can temporarily revert to the old client-side deletion:

1. **Keep migration applied** (function doesn't hurt)
2. **Restore old endpoint code** from git:
   ```bash
   git show HEAD~1:backend/app/api/v1/documents.py > temp.py
   # Copy the delete_document function back
   ```
3. **Re-add ChunkRepository import**

Then investigate and fix the RPC approach before re-deploying.

---

## Future Enhancements

**Phase 6 Considerations:**

- Update RPC function to use Clerk JWT instead of `auth.uid()`
- Add soft-delete support (mark deleted, don't physically remove)
- Add audit logging to track who deleted what and when
- Consider batch deletion RPC for multiple documents

**Monitoring:**

- Add metrics for deletion performance
- Track rollback frequency (should be near zero)
- Log slow deletions (>1s indicates index issues)

---

## Technical References

**Why RPC over Client Transactions?**

1. Supabase Python client doesn't expose PostgreSQL's BEGIN/COMMIT
2. PostgreSQL functions run in implicit transaction blocks
3. Consistent with Supabase Auth, Storage, and other features
4. Better performance (server-side execution)

**PostgreSQL Transaction Guarantees:**

- All statements in a function are atomic by default
- Any `RAISE EXCEPTION` triggers automatic rollback
- No explicit BEGIN/COMMIT needed in function body
- ACID compliance is PostgreSQL's core strength

**RLS with SECURITY INVOKER:**

- Function executes with caller's user_id (from JWT)
- RLS policies automatically apply to all queries
- `auth.uid()` in RLS matches the JWT user
- Cannot delete another user's documents

---

## Testing Checklist

- [x] Migration creates function successfully
- [x] Function grants execute to authenticated/anon
- [x] RLS prevents cross-user deletion
- [x] Atomic rollback verified manually
- [x] API endpoint uses new RPC method
- [x] Old ChunkRepository import removed
- [x] No lint/type errors
- [x] Test suite covers all scenarios
- [x] Documentation updated
- [x] Migration README updated

---

## Conclusion

This implementation provides production-grade atomic deletion with true ACID guarantees. The PostgreSQL RPC approach is the industry-standard solution for transaction management when client libraries don't support explicit transactions.

**Key Takeaway:** Always prefer database-native transaction mechanisms over client-side compensating strategies when data integrity is critical.
