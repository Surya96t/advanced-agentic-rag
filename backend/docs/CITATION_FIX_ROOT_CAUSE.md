# Citation Fix - Complete Root Cause Analysis

## Problem Summary

Citations were not appearing in the chat UI despite the database containing the correct data and SQL functions returning `document_title` correctly.

## Root Cause Analysis

### Database Schema (CORRECT ✅)

```sql
-- document_chunks table has:
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY,           -- ✅ Chunk identifier
    document_id UUID,               -- ✅ Foreign key to documents
    content TEXT,
    metadata JSONB,
    embedding VECTOR(1536),
    search_vector TSVECTOR,
    ...
)

-- documents table has:
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    title TEXT,                     -- ✅ Document title
    ...
)
```

### SQL Functions (CORRECT ✅)

Both functions were correctly updated in migration 007:

- `search_chunks_by_embedding()` - Returns `id`, `document_id`, `document_title` ✅
- `search_chunks_by_text()` - Returns `id`, `document_id`, `document_title` ✅

### Python Code Issues (FOUND 3 BUGS ❌)

#### Bug #1: `hybrid_search.py` Line 308

**Issue:** When fusing vector + text results, the code was not copying `document_title`

```python
# BEFORE (BROKEN):
SearchResult(
    chunk_id=chunk_id,
    document_id=base_result.document_id,
    content=base_result.content,  # ❌ Missing document_title!
    ...
)

# AFTER (FIXED):
SearchResult(
    chunk_id=chunk_id,
    document_id=base_result.document_id,
    document_title=base_result.document_title,  # ✅ Added!
    content=base_result.content,
    ...
)
```

#### Bug #2: `flashrank.py` Line 170 & 206

**Issue:** When re-ranking results, document_title was not preserved

```python
# BEFORE (BROKEN):
passages = [{
    "meta": {
        "chunk_id": str(result.chunk_id),
        "document_id": str(result.document_id),
        # ❌ Missing document_title!
    }
}]

# AFTER (FIXED):
passages = [{
    "meta": {
        "chunk_id": str(result.chunk_id),
        "document_id": str(result.document_id),
        "document_title": result.document_title,  # ✅ Added!
    }
}]
```

#### Bug #3: `vector_search.py` Line 263

**Issue:** The `search_by_embedding()` method was missing `document_title`

```python
# BEFORE (BROKEN):
SearchResult(
    chunk_id=UUID(row["id"]),
    document_id=UUID(row["document_id"]),
    content=row["content"],  # ❌ Missing document_title!
    ...
)

# AFTER (FIXED):
SearchResult(
    chunk_id=UUID(row["id"]),
    document_id=UUID(row["document_id"]),
    document_title=row.get("document_title", "Unknown Document"),  # ✅ Added!
    content=row["content"],
    ...
)
```

## Why This Caused No Citations

1. ✅ Database had document titles
2. ✅ SQL functions returned document titles
3. ✅ Vector search (main path) included document_title
4. ✅ Text search included document_title
5. ❌ **Hybrid search** dropped document_title when fusing results
6. ❌ Pydantic validation failed: `document_title` field required
7. ❌ Error caught, no citations emitted
8. ❌ Frontend received empty citations array

## Data Flow (FIXED)

```
Database (SQL Function)
  ↓
  Returns: {id, document_id, document_title, content, metadata, score}
  ↓
Vector Search → SearchResult (✅ has document_title)
Text Search   → SearchResult (✅ has document_title)
  ↓
Hybrid Search (RRF Fusion)
  ↓
  BEFORE: SearchResult (❌ missing document_title) → VALIDATION ERROR
  AFTER:  SearchResult (✅ has document_title) → SUCCESS
  ↓
Reranker (if enabled)
  ↓
  BEFORE: SearchResult (❌ missing document_title) → VALIDATION ERROR
  AFTER:  SearchResult (✅ has document_title) → SUCCESS
  ↓
Retriever Node → Emits Citation Events
  ↓
Frontend → Displays Sources/Citations
```

## Files Modified

1. `/backend/app/retrieval/hybrid_search.py` (Line 308)
2. `/backend/app/retrieval/rerankers/flashrank.py` (Lines 170, 206)
3. `/backend/app/retrieval/vector_search.py` (Line 263)

## Testing

Run the chat now and ask any question. You should see:

### Backend Logs:

```
{"event": "Processing 3 sources from retriever", ...}
{"event": "Source: chunk_id=..., document_id=..., title=01_proposed_node_architecture.md"}
```

### Browser Console:

```javascript
[Citation Event] {
  chunk_id: "d222040c-4ce4-49d4-8e31-e12179e49acc",
  document_title: "01_proposed_node_architecture.md",  // ✅ REAL TITLE!
  score: 0.85
}
```

### Frontend UI:

- Sources section appears below AI response
- Real document titles instead of "Unknown Document"
- Clickable citation badges in text

## Conclusion

The issue was **not** in the database or SQL functions. The migration 007 was correct. The issue was in the **Python data transformation layer** where SearchResult objects were created without including the `document_title` field that the SQL functions were correctly returning.

All 3 bugs have been fixed, and the backend will hot-reload automatically. Citations should now work! 🎉
