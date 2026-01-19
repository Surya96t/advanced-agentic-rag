Here is the **API Specification Document** (The Contract).

This document bridges the gap between your Next.js Frontend and your FastAPI Backend. It ensures that when you start coding, you won't have to stop and guess "Wait, did I call this field `text` or `content`?"

Save this as `api-contract.md`.

---

# 🔌 API Specification & Data Contract: Project "Integration Forge"

**Version:** 1.0
**Date:** January 7, 2026
**Protocol:** REST + Server-Sent Events (SSE) for Streaming
**Base URL (Local):** `http://localhost:8000`

---

## 1. Authentication & Security

- **Strategy:** Bearer Token (Stateless).
- **Header:** All requests to protected endpoints **must** include:
  ```http
  Authorization: Bearer <clerk_session_jwt>
  ```
- **Validation:** The Backend validates this token against Clerk's JWKS. If invalid or expired, returns `401 Unauthorized`.
- **User Identity:** The Backend extracts `sub` (User ID) from the token to enforce RLS logic.

---

## 2. Shared Data Models (DTOs)

_These definitions correspond to Pydantic models in Python and TypeScript Interfaces in Next.js._

### `IngestRequest`

Used when triggering the backend to process a file that was just uploaded to Supabase Storage.

```json
{
  "source_id": "uuid-string", // The 'Library' this belongs to
  "document_id": "uuid-string", // The DB ID of the document row
  "blob_path": "user_123/docs/file.md", // Path in Supabase Storage
  "title": "Clerk Webhooks.md" // Display title
}
```

### `ChatRequest`

Used to send a user message to the Agent.

```json
{
  "chat_id": "uuid-string", // The session ID
  "message": "How do I sync users?", // The User's new input
  "selected_source_ids": [
    // Which 'folders' to search in
    "uuid-1",
    "uuid-2"
  ],
  "model": "gpt-4o" // Optional: default to config
}
```

---

## 3. Endpoints

### 🩺 Health Check

**GET** `/health`

- **Purpose:** Check if API and DB connection are alive.
- **Response:** `200 OK` `{"status": "ok", "db": "connected"}`

---

### 📥 Ingestion (The Pipeline)

**POST** `/api/v1/ingest`

- **Purpose:** Triggers the background worker to download, parse, chunk, and embed a file.
- **Prerequisite:** The Frontend must have _already_ uploaded the file to Supabase Storage and created the row in the `documents` table with status `pending`.
- **Request Body:** `IngestRequest` (see above).
- **Response:**
  - `202 Accepted`: Processing started in background.
  - `{"task_id": "uuid", "status": "processing"}`

---

### 💬 Chat (The Agent Stream)

**POST** `/api/v1/chat`

- **Purpose:** Main interaction point. Streams the Agent's reasoning and response.
- **Request Body:** `ChatRequest` (see above).
- **Response Content-Type:** `text/event-stream` (SSE).
- **Stream Events:**
  The stream will emit named events to update the UI in real-time.

  **Event 1: `status`** (Updates the "Thinking..." pill)

  ```json
  event: status
  data: {"step": "planning", "message": "Analyzing request..."}
  ```

  **Event 2: `status`** (Update)

  ```json
  event: status
  data: {"step": "retrieving", "message": "Searching Clerk Docs..."}
  ```

  **Event 3: `citation`** (When sources are found)

  ```json
  event: citation
  data: {
    "source_id": "uuid",
    "document_title": "Clerk Docs",
    "chunk_id": "uuid",
    "relevance_score": 0.89
  }
  ```

  **Event 4: `token`** (The actual answer text appearing letter-by-letter)

  ```json
  event: token
  data: "To "
  ```

  ```json
  event: token
  data: "integrate "
  ```

  **Event 5: `end`** (Stream complete)

  ```json
  event: end
  data: {"done": true}
  ```

---

### 🗑️ Document Management

**DELETE** `/api/v1/documents/{document_id}`

- **Purpose:** Deletes a document **AND** its vectors.
- **Logic:**
  1.  Delete vectors from `document_chunks` table (pgvector).
  2.  Delete row from `documents` table.
  3.  Delete file from Supabase Storage.
- **Response:** `200 OK` `{"deleted": true}`

---

## 4. Error Handling Standards

The Backend will return standard HTTP codes with a JSON error body:

```json
{
  "error": "ERR_CODE",
  "message": "Human readable description",
  "detail": "Technical detail (optional)"
}
```

- **400 Bad Request:** Malformed JSON or missing fields.
- **401 Unauthorized:** Missing/Invalid Clerk Token.
- **403 Forbidden:** RLS violation (Trying to delete someone else's doc).
- **429 Too Many Requests:** OpenAI rate limit hit or user credit limit hit.
- **500 Internal Error:** Python exception (e.g., OpenAI API down).

---

# ✅ Planning Phase Complete

This was the final missing piece.

1.  **Architecture:** Defined (Next.js + FastAPI + Supabase).
2.  **Database:** Designed (Tables + RLS + Hybrid Search cols).
3.  **Strategy:** Locked (Markdown Chunking + Hybrid Search + LangGraph Loop).
4.  **Interface:** Defined (This API Contract).

You are now officially ready to enter **Phase 2: Implementation**.

**Suggestion:** Start by initializing the **Supabase Project** (Database) first, as both the Frontend and Backend depend on it existing.

Shall we switch modes to **Implementation** and start with the Database Setup?
