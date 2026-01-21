# Phase 2: Document Ingestion - Task Tracker

**Goal:** Upload document → Parse → Chunk → Embed → Store in Supabase

---

## Tasks

- [x] 1. Database Models (`app/database/models.py`) ✅
- [x] 2. Document Schemas (`app/schemas/document.py`) ✅
- [x] 3. Document Repository (`app/database/repositories/documents.py`) ✅
- [x] 4. Chunk Repository (`app/database/repositories/chunks.py`) ✅
- [x] 5. Parser (`app/ingestion/parser.py`) ✅
- [x] 6. Base Chunker (`app/ingestion/chunkers/base.py`) ✅
- [x] 7. Recursive Chunker (`app/ingestion/chunkers/recursive.py`) ✅
- [x] 8. Embeddings Client (`app/ingestion/embeddings.py`) ✅
- [x] 9. Ingestion Pipeline (`app/ingestion/pipeline.py`) ✅
- [ ] 10. Ingest API Endpoint (`app/api/v1/ingest.py`)

---

## Testing Checkpoints

- [x] Can parse Markdown file → extract text ✅
- [x] Can chunk text → verify overlap works ✅
- [x] Can generate embeddings → verify vector dimensions ✅
- [x] Can store in Supabase → query chunks table ✅
- [x] Integration test: Full pipeline with real documents ✅
- [x] Migration: Clerk-compatible user IDs (TEXT instead of UUID) ✅
- [ ] End-to-end: Upload file via API → see chunks in database

---

## Recent Migrations

- [x] **Migration 003: Clerk User ID Compatibility** ✅
  - Reverted all `user_id` columns from UUID to TEXT for Clerk integration
  - Updated RLS policies to work with TEXT user IDs
  - Updated all models, repositories, and pipeline code
  - All integration tests passing with Clerk-style IDs (e.g., "user_test_abc123")
  - Database schema verified in production Supabase instance

---

## Next: Task 10 - Ingest API Endpoint

**File:** `app/api/v1/ingest.py`

**Requirements:**
- FastAPI endpoint for document upload (`POST /api/v1/ingest`)
- Accept multipart/form-data (file upload)
- Extract user_id from Clerk JWT token (auth middleware)
- Call IngestionPipeline with progress tracking
- Return document ID and status
- Support SSE streaming for progress updates (optional)

**Dependencies:**
- Clerk JWT validation (`app/core/auth.py`)
- Rate limiting per user
- File size validation
- Supported file types: PDF, Markdown, Text

---

**Delete this file after Phase 2 completion**
