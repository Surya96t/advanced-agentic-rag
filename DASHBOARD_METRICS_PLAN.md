# Dashboard Metrics Implementation Plan

## Objective
Populate the static dashboard metrics in `frontend/app/(dashboard)/dashboard/page.tsx` with dynamic data from the backend. The metrics to populate are:
1. **Documents**: Total number of documents uploaded by the user.
2. **Chunks**: Total number of vector chunks generated from user documents.
3. **Conversations**: Total number of active chat threads for the user.
4. **Queries**: Total number of user interactions (messages sent).

## Architecture
- **Source of Truth**: Supabase Database (PostgreSQL).
- **Observability**: While LangSmith is used for tracing, for low-latency dashboard rendering, we will query the operational database directly rather than the LangSmith API.
- **Data Access**: 
    - `documents` table for document counts.
    - `document_chunks` table for chunk counts.
    - `checkpoints` table (LangGraph persistence) for conversation and query counts.

---

## Part 1: Backend Implementation (`/backend`)

### 1. Create Stats Endpoint
**File**: `backend/app/api/v1/stats.py` (New File)

**Responsibility**: 
- Authenticate the user via `UserID` dependency.
- Efficiently query the database for the 4 metrics.

**Implementation Details**:
- **Endpoint**: `GET /api/v1/stats`
- **Response Schema**:
  ```python
  class DashboardStats(BaseModel):
      documents_count: int      # Count from 'documents' table
      chunks_count: int         # Count from 'document_chunks' table
      conversations_count: int  # Count unique thread_ids in 'checkpoints'
      queries_count: int        # Derived from 'message_count' in thread metadata
  ```
- **Logic**:
  1. **Documents & Chunks**: Use `SupabaseClient` to perform a `count` query filtered by `user_id`.
  2. **Conversations**: Query the `checkpoints` table for distinct `thread_id`s where `user_id` matches.
  3. **Queries**: 
     - *Challenge*: We don't have a dedicated "user_messages" table.
     - *Solution*: Start with a placeholder or simple estimation (e.g., sum of `message_count` / 2 from thread metadata) to avoid scanning heavy JSON blobs in real-time. We can refine this to specific `role="user"` counts in a future migration if precision is critical.

### 2. Register Router
**File**: `backend/app/api/v1/__init__.py`

**Action**:
- Import `stats.router`.
- Include it in the main API router with tag `["stats"]`.

---

## Part 2: Frontend Implementation (`/frontend`)

### 1. Update API Client Types
**File**: `frontend/types/dashboard.ts` (New or update existing)

**Action**:
- Define the TypeScript interface for the stats response.
  ```typescript
  export interface DashboardStats {
    documents_count: number
    chunks_count: number
    conversations_count: number
    queries_count: number
  }
  ```

### 2. refactor Dashboard Page
**File**: `frontend/app/(dashboard)/dashboard/page.tsx`

**Action**:
- Convert to **Async Server Component** (`export default async function...`).
- Implement data fetching:
  ```typescript
  async function getDashboardStats(): Promise<DashboardStats> {
    return await apiJSON<DashboardStats>('/api/v1/stats');
  }
  ```
- Replace static "0" values with `stats.documents_count`, etc.
- Add error handling (try/catch) to return zero-values if the backend call fails, preventing page crash.
