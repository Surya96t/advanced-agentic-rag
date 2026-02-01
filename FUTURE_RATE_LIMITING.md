# Future Backend Enhancements - Rate Limiting

## Overview

Currently, only the chat endpoints (`/api/v1/chat` and `/api/v1/chat/stream`) return rate limit headers. This document tracks the work needed to add rate limit headers to all endpoints.

---

## Current Status

### ✅ Endpoints WITH Rate Limit Headers:

- `POST /api/v1/chat` (non-streaming)
- `POST /api/v1/chat/stream` (SSE streaming)

**Headers returned:**

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1738454400
```

### ❌ Endpoints WITHOUT Rate Limit Headers:

- `GET /api/v1/documents` (limit: 200/hour)
- `POST /api/v1/ingest` (limit: 20/hour)
- `DELETE /api/v1/documents/{id}` (uses document limit)

---

## Implementation Plan

### Backend Changes Required

**File:** `backend/app/api/v1/documents.py`

Add rate limit headers to response:

```python
# In list_documents endpoint (GET)
response.headers["X-RateLimit-Limit"] = str(limit)
response.headers["X-RateLimit-Remaining"] = str(remaining)
response.headers["X-RateLimit-Reset"] = str(reset_time)
```

**File:** `backend/app/api/v1/ingest.py`

Add rate limit headers to response:

```python
# In ingest_document endpoint (POST)
response.headers["X-RateLimit-Limit"] = str(limit)
response.headers["X-RateLimit-Remaining"] = str(remaining)
response.headers["X-RateLimit-Reset"] = str(reset_time)
```

### Frontend Changes Required

**File:** `frontend/app/api/documents/route.ts`

Extract and forward rate limit headers from backend to frontend.

**File:** `frontend/app/(dashboard)/documents/page.tsx`

Display rate limit info in documents page (similar to chat).

---

## Priority

**Priority:** Low (Nice to have)

**Reason:**

- Chat is the primary interactive feature and already has rate limiting display
- Document operations are less frequent
- Can be added in a future update

---

## Estimated Effort

- **Backend:** 1-2 hours (add headers to 3 endpoints)
- **Frontend:** 1-2 hours (extract and display headers)
- **Testing:** 30 minutes

**Total:** 3-4 hours

---

## Next Steps

1. Add rate limit headers to backend endpoints
2. Update frontend BFF handlers to forward headers
3. Add rate limit display to documents page
4. Test end-to-end
5. Update documentation

---

**Created:** February 1, 2026  
**Status:** Backlog
