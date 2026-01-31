# Integration Forge - Frontend Continuation Prompt

**Date:** January 25, 2026  
**Project:** Integration Forge - Advanced Agentic RAG System  
**Current Phase:** Frontend Implementation - Checkpoint 5 (Polish & Performance)

---

## 🎯 Project Context

**Integration Forge** is a production-grade RAG (Retrieval-Augmented Generation) system that helps developers synthesize integration code from siloed API documentation.

### Tech Stack

**Backend:**

- FastAPI (Python)
- LangGraph for agentic workflows
- Supabase (PostgreSQL + pgvector)
- OpenAI (embeddings + LLM)
- Clerk (JWT authentication)

**Frontend:**

- Next.js 16.1.4 (App Router)
- React 19.2.3
- TypeScript (strict mode)
- Tailwind CSS 4.x
- shadcn/ui v2
- Clerk Auth
- BFF (Backend-for-Frontend) architecture

**Architecture:**

```
Browser → Next.js Route Handlers (BFF) → FastAPI Backend
  (UI)      (Proxy + JWT forwarding)      (Agentic RAG)
```

---

## ✅ What's Been Completed

### Backend (95% Complete) ✅

- ✅ Supabase integration with pgvector
- ✅ Document ingestion pipeline (5 chunking strategies)
- ✅ Hybrid search (dense vector + sparse text + RRF fusion)
- ✅ Re-ranking (FlashRank + Cohere)
- ✅ LangGraph agentic RAG workflow (router → query_expander → retriever → generator → validator)
- ✅ Clerk JWT authentication with RLS policies
- ✅ Rate limiting with Redis
- ✅ SSE streaming for real-time responses
- ✅ Comprehensive error handling and logging

**Backend Endpoints:**

```
✅ GET  /health                    - Health check
✅ GET  /api/v1/documents          - List user documents
✅ POST /api/v1/ingest             - Upload & process document
✅ DELETE /api/v1/documents/{id}   - Delete document
✅ POST /api/v1/chat               - Chat (SSE streaming)
✅ POST /api/v1/users/sync         - Sync Clerk user to DB
```

---

### Frontend (80% Complete) ✅

#### ✅ Checkpoint 1: BFF Foundation & Auth (100%)

- ✅ Next.js 16.1.4 with App Router and Turbopack
- ✅ TypeScript strict mode
- ✅ Tailwind CSS 4.x (Oxide engine)
- ✅ shadcn/ui v2 configured (New York style)
- ✅ Clerk authentication integrated (server-side `auth()`)
- ✅ BFF Route Handlers structure (`app/api/`)
- ✅ JWT token extraction and forwarding to backend
- ✅ Protected routes with Clerk middleware
- ✅ Dashboard layout with navigation and user button

**shadcn/ui Components Installed:**

```bash
✅ button, card, input, skeleton
✅ dialog, progress, badge, separator, scroll-area, sonner, table
✅ textarea, avatar
```

---

#### ✅ Checkpoint 2: Document Upload UI (100%)

- ✅ Upload page with file selection
- ✅ Document list with table view (Server Component)
- ✅ BFF Route Handlers:
  - ✅ `GET/POST /api/documents` - List & upload documents
  - ✅ `DELETE /api/documents/[id]` - Delete document
- ✅ File validation (PDF, MD, TXT, max 10MB)
- ✅ Upload progress tracking
- ✅ Delete confirmation dialog
- ✅ Toast notifications (Sonner)
- ✅ Empty state for no documents
- ✅ User sync on login (Clerk → Supabase)

**Files:**

- `/app/(dashboard)/upload/page.tsx` - Upload page
- `/app/api/documents/route.ts` - List & upload BFF handler
- `/app/api/documents/[id]/route.ts` - Delete BFF handler
- `/components/upload/file-upload.tsx` - File upload component
- `/components/upload/document-list.tsx` - Document list component

---

#### ✅ Checkpoint 3: Chat Interface (100%)

- ✅ Chat page created (`app/(dashboard)/chat/page.tsx`)
- ✅ Message components (user and AI message bubbles)
- ✅ Message input with auto-resize textarea
- ✅ Custom `useChat` hook with Zustand state management
- ✅ BFF route handler for chat (`app/api/chat/route.ts`)
- ✅ Markdown rendering for AI responses (react-markdown)
- ✅ Citation components (badges with document references)
- ✅ Auto-scroll to latest message

**Files:**

- `/app/(dashboard)/chat/page.tsx` - Chat page
- `/app/api/chat/route.ts` - Chat BFF handler (SSE streaming)
- `/hooks/useChat.ts` - Custom chat hook
- `/stores/chat-store.ts` - Zustand store for chat state
- `/components/chat/message-list.tsx` - Message list component
- `/components/chat/message-bubble.tsx` - Message bubble component
- `/components/chat/message-input.tsx` - Message input component
- `/components/chat/citation.tsx` - Citation badge component
- `/lib/sse-parser.ts` - SSE parsing utility

---

#### ✅ Checkpoint 4: SSE Streaming (100%)

- ✅ SSE streaming working end-to-end
- ✅ Token-by-token message rendering
- ✅ Agent status indicators (router, query_expander, retriever, generator, validator)
- ✅ Progressive citation display
- ✅ All SSE events handled:
  - ✅ `agent_start` - Agent begins processing
  - ✅ `agent_complete` - Agent finishes
  - ✅ `progress` - Status updates
  - ✅ `token` - AI-generated text chunks
  - ✅ `citation` - Source document references
  - ✅ `validation` - Quality validation results
  - ✅ `end` - Stream complete
- ✅ Typing indicator during streaming
- ✅ Smooth scroll during streaming
- ✅ Error handling and recovery

**Event Flow:**

```
1. User sends message
2. Frontend calls POST /api/chat (BFF)
3. BFF forwards to POST /api/v1/chat (FastAPI SSE)
4. Backend streams events: agent_start → progress → token → citation → validation → end
5. Frontend parses SSE events and updates UI in real-time
6. Messages stream token-by-token, citations appear progressively
```

---

#### 🔄 Checkpoint 5: Polish & Performance (60% Complete)

**What's Working:**

- ✅ Error boundaries (route-level)
- ✅ Loading skeletons for document list
- ✅ Toast notifications for user feedback
- ✅ Clerk UserButton hydration fix (client-only wrapper)
- ✅ Responsive layout (basic mobile support)

**Recent Fixes Applied:**

- ✅ Fixed duplicate citation keys (React warning)
- ✅ Fixed stream controller closing error (invalid state)
- ✅ Lowered validator quality threshold (0.7 → 0.5) to reduce retries
- ✅ Added performance timing logs to backend retrieval
- ✅ Fixed markdown rendering (full response as single token)
- ✅ Fixed auto-scroll and scroll-up support
- ✅ Fixed event schema mismatches between backend and frontend
- ✅ Fixed prepared statement errors (Supabase Transaction Pooler)

---

## 🚨 Current Issues

### 1. Performance - Slow Retrieval (HIGH PRIORITY)

**Problem:**

- Retrieval takes 3-5 minutes per query
- Validator retries cause multiple retrieval runs (up to 3x)
- User sees "Searching documentation..." for extended periods

**Root Cause:**

- Validator quality score often falls below threshold (now 0.5, was 0.7)
- Each retry triggers full pipeline: query_expansion → retrieval → generation → validation
- Retrieval involves:
  - OpenAI embedding generation (network call)
  - Vector search (database query)
  - Text search (database query)
  - Re-ranking (FlashRank model inference)

**What's Been Done:**

- ✅ Lowered validator threshold from 0.7 to 0.5 (reduces retries)
- ✅ Added timing logs to identify bottlenecks:
  - `vector_search.py`: Embedding generation time
  - `vector_search.py`: Database search time
  - `text_search.py`: Database query time

**What's Needed:**

- [ ] Analyze timing logs to identify bottleneck (embedding vs database vs re-ranking)
- [ ] Optimize retrieval performance:
  - Option A: Reduce `top_k` from 10 to 5 (fewer results, faster queries)
  - Option B: Enable parallel vector + text search (currently sequential)
  - Option C: Cache embeddings for common queries (Redis)
  - Option D: Skip re-ranking for faster responses (or use lighter model)
- [ ] Further tune validator threshold or disable certain checks
- [ ] Add loading indicators with estimated time
- [ ] Consider adding "Cancel" button for long queries

**Files to Check:**

- `/backend/app/retrieval/vector_search.py` - Vector search with timing logs
- `/backend/app/retrieval/text_search.py` - Text search with timing logs
- `/backend/app/retrieval/hybrid_search.py` - Hybrid search orchestration
- `/backend/app/agents/nodes/retriever.py` - Retrieval node (calls searchers)
- `/backend/app/agents/nodes/validator.py` - Validation node (threshold = 0.5)
- `/backend/server.log` - Timing logs output

---

### 2. Rate Limit UI (Not Implemented)

**What's Missing:**

- No visual indicator when approaching rate limits
- No banner when rate limit is hit (429 response)
- No countdown timer showing when limit resets

**What's Needed:**

- [ ] Parse `X-RateLimit-Remaining` and `X-RateLimit-Reset` headers in BFF
- [ ] Create rate limit banner component (shadcn `Alert`)
- [ ] Display countdown timer until reset
- [ ] Disable chat input when rate limited
- [ ] Show remaining quota in header (optional)

**Rate Limits (from Backend):**

- Ingest: 20 requests/hour
- Chat: 100 requests/hour
- Documents: 200 requests/hour

---

### 3. Mobile Responsive Polish (Partial)

**What's Working:**

- ✅ Basic responsive layout
- ✅ Mobile-friendly buttons and inputs

**What's Missing:**

- [ ] Chat UI optimizations for mobile (smaller screens)
- [ ] Touch-friendly scrolling
- [ ] Collapsible navigation on mobile
- [ ] Optimized citation display on small screens
- [ ] Virtual keyboard handling (iOS Safari)

---

### 4. Accessibility (Not Audited)

**What's Missing:**

- [ ] ARIA labels on interactive elements
- [ ] Keyboard navigation (Tab, Enter, Escape)
- [ ] Focus indicators (Tailwind `focus-visible:`)
- [ ] Screen reader announcements (live regions for streaming)
- [ ] Color contrast audit (WCAG AA)

---

## 📋 TODO: Checkpoint 5 Completion Tasks

### High Priority (Performance & Error Handling)

1. **[ ] Performance Analysis**
   - Review backend timing logs (`tail -f backend/server.log`)
   - Identify bottleneck: embedding generation vs database vs re-ranking
   - Document findings in issue or comment

2. **[ ] Optimize Retrieval Speed**
   - Reduce `top_k` from 10 to 5 in `/backend/app/retrieval/hybrid_search.py`
   - Test if parallel vector + text search improves speed
   - Consider caching embeddings in Redis
   - Consider skipping re-ranking or using lighter model

3. **[ ] Rate Limit UI Implementation**
   - Create `components/ui/rate-limit-banner.tsx`
   - Parse rate limit headers in BFF route handlers
   - Display banner with countdown timer
   - Disable chat input when rate limited

4. **[ ] Error Pages**
   - Create `app/error.tsx` (route-level error boundary)
   - Create `app/not-found.tsx` (404 page)
   - Create custom error pages for 401, 429, 500

5. **[ ] Loading States Polish**
   - Add loading skeleton for chat history (if implemented)
   - Add spinner for message sending
   - Add estimated time indicator for long queries
   - Consider "Cancel" button for ongoing queries

---

### Medium Priority (UI Polish)

6. **[ ] Mobile Responsive Refinements**
   - Test chat UI on mobile (320px, 375px, 414px widths)
   - Optimize citation badges for small screens
   - Add collapsible sidebar/navigation
   - Test keyboard behavior on iOS Safari

7. **[ ] Accessibility Audit**
   - Add ARIA labels to all interactive elements
   - Ensure keyboard navigation works (Tab, Enter, Escape)
   - Add focus indicators (Tailwind `focus-visible:`)
   - Test with screen reader (VoiceOver on macOS)
   - Add live regions for streaming messages

8. **[ ] Animation & Transition Polish**
   - Smooth fade-in for new messages
   - Smooth scroll-to-bottom animation
   - Loading spinner animation
   - Citation badge hover effects

9. **[ ] Empty States Polish**
   - Improve "No documents" empty state
   - Add "No messages" empty state in chat
   - Add helpful prompts and suggestions

---

### Low Priority (Nice-to-Have)

10. **[ ] Bundle Size Optimization**
    - Run bundle analyzer (`next build --analyze`)
    - Check for large dependencies
    - Implement code splitting if needed

11. **[ ] Lighthouse Audit**
    - Run Lighthouse in Chrome DevTools
    - Optimize Core Web Vitals (LCP, FID, CLS)
    - Fix any performance or accessibility issues

12. **[ ] Image Optimization**
    - Use Next.js `Image` component for any images
    - Optimize icons and logos

13. **[ ] Documentation**
    - Update README with setup instructions
    - Add screenshots to docs
    - Document environment variables
    - Create deployment guide

---

## 🎯 Recommended Next Steps

### Step 1: Analyze Performance Bottleneck (30 min)

1. Send a test query in the chat UI
2. Monitor backend logs: `tail -f backend/server.log | grep -E "(Embedding|Database|Text search)"`
3. Look for timing logs:
   - `"Embedding generation took X.XXs"`
   - `"Database search took X.XXs"`
   - `"Text search database query took X.XXs"`
4. Identify which operation is slowest

### Step 2: Optimize Based on Findings (1-2 hours)

**If embedding generation is slow (>5s):**

- Implement embedding cache in Redis
- Consider batch embedding generation

**If database queries are slow (>5s):**

- Check Supabase dashboard for slow queries
- Verify HNSW index is being used
- Reduce `top_k` from 10 to 5

**If re-ranking is slow (>5s):**

- Skip re-ranking (set `reranker = None`)
- Use lighter FlashRank model
- Reduce re-ranking `top_k` from 5 to 3

**If validator is causing retries:**

- Further lower threshold to 0.4
- Disable specific checks (e.g., source attribution)
- Skip validation entirely for testing

### Step 3: Implement Rate Limit UI (2-3 hours)

1. Create rate limit banner component
2. Parse headers in BFF route handlers
3. Store rate limit state in Zustand
4. Display banner when rate limit hit
5. Show countdown timer until reset

### Step 4: Mobile & Accessibility Polish (3-4 hours)

1. Test on mobile devices (real or Chrome DevTools)
2. Fix any layout issues
3. Add ARIA labels
4. Test keyboard navigation
5. Run Lighthouse audit

---

## 📂 Key Files Reference

### Frontend Structure

```
frontend/
├── app/
│   ├── (dashboard)/
│   │   ├── chat/page.tsx              # Chat interface
│   │   ├── upload/page.tsx            # Document upload
│   │   └── layout.tsx                 # Dashboard layout
│   ├── api/
│   │   ├── chat/route.ts              # Chat BFF (SSE streaming)
│   │   ├── documents/route.ts         # Documents BFF (list & upload)
│   │   └── documents/[id]/route.ts    # Delete document BFF
│   └── layout.tsx                     # Root layout (Clerk provider)
├── components/
│   ├── auth/
│   │   └── user-button-wrapper.tsx    # Clerk UserButton (client-only)
│   ├── chat/
│   │   ├── message-list.tsx           # Message list with auto-scroll
│   │   ├── message-bubble.tsx         # User/AI message bubbles
│   │   ├── message-input.tsx          # Chat input with auto-resize
│   │   └── citation.tsx               # Citation badges
│   └── upload/
│       ├── file-upload.tsx            # File upload component
│       └── document-list.tsx          # Document list table
├── hooks/
│   └── useChat.ts                     # Custom chat hook (SSE streaming)
├── stores/
│   └── chat-store.ts                  # Zustand store (chat state)
├── lib/
│   ├── api-client.ts                  # BFF API client
│   └── sse-parser.ts                  # SSE event parser
└── types/
    └── chat.ts                        # Chat-related types
```

### Backend Structure (Relevant for Performance)

```
backend/
├── app/
│   ├── agents/
│   │   ├── graph.py                   # LangGraph workflow definition
│   │   └── nodes/
│   │       ├── router.py              # Router node
│   │       ├── query_expander.py      # Query expansion node
│   │       ├── retriever.py           # Retrieval node (calls searchers)
│   │       ├── generator.py           # Response generation node
│   │       └── validator.py           # Validation node (threshold=0.5)
│   ├── retrieval/
│   │   ├── hybrid_search.py           # Hybrid search orchestration
│   │   ├── vector_search.py           # Vector search (with timing logs)
│   │   └── text_search.py             # Text search (with timing logs)
│   └── api/v1/
│       └── chat.py                    # SSE streaming endpoint
└── server.log                         # Timing logs output
```

---

## 🔑 Important Context for Next Session

### Environment Variables (Frontend)

```bash
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Environment Variables (Backend)

```bash
OPENAI_API_KEY=sk-proj-...
SUPABASE_URL=https://vbmkukyjtbryynhyfldv.supabase.co
CLERK_SECRET_KEY=sk_test_...
CLERK_ISSUER_URL=https://prime-lynx-87.clerk.accounts.dev
PGPREPARE_THRESHOLD=0  # Critical for Supabase Transaction Pooler
```

### Running the Project

```bash
# Backend (port 8000)
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (port 3000)
cd frontend
pnpm dev
```

### Current Validator Settings

- Quality threshold: **0.5** (lowered from 0.7)
- Max retries: **2**
- Validation checks:
  - Source attribution (30% weight)
  - Code completeness (25% weight)
  - Grounding in sources (30% weight)
  - Retrieval confidence (15% weight)

### Known Working Features

- ✅ Authentication (Clerk)
- ✅ Document upload and management
- ✅ Chat interface with SSE streaming
- ✅ Token-by-token message rendering
- ✅ Agent status indicators
- ✅ Progressive citation display
- ✅ Markdown rendering
- ✅ Auto-scroll during streaming
- ✅ Error boundaries and toast notifications

---

## 🎯 Success Criteria for Completion

**Checkpoint 5 Complete When:**

- [ ] Retrieval performance is acceptable (<30 seconds per query)
- [ ] Rate limit UI displays and handles 429 responses
- [ ] Mobile responsive on all screen sizes (320px - 1920px)
- [ ] Accessibility audit passes (WCAG AA)
- [ ] Error pages created (401, 429, 500, 404)
- [ ] Loading states polished with proper indicators
- [ ] Lighthouse score >90 for Performance, Accessibility, Best Practices

**Overall Project Complete When:**

- [ ] All features working end-to-end
- [ ] Performance optimized (<30s query, <2s page load)
- [ ] Production-ready error handling
- [ ] Mobile and desktop responsive
- [ ] Accessible (WCAG AA compliant)
- [ ] Documentation complete
- [ ] Ready for deployment

---

## 📝 Additional Notes

- Backend FastAPI server runs on port 8000
- Frontend Next.js runs on port 3000
- Clerk handles all authentication (JWT tokens)
- Supabase handles data storage and vector search
- LangGraph orchestrates agentic RAG workflow
- All backend requests go through BFF Route Handlers (CORS eliminated)
- SSE streaming is fully functional (backend → BFF → frontend)
- Validator retries are the main performance bottleneck currently

---

**Status:** Ready to optimize performance and complete final polish! 🚀

---

**Questions to Ask in Next Session:**

1. What are the timing logs showing? (embedding vs database vs re-ranking)
2. What's an acceptable query response time? (target: <30s)
3. Should we prioritize speed over quality? (skip re-ranking, lower threshold further)
4. Do we need conversation history persistence? (optional Checkpoint 6)
5. What's the deployment target? (Vercel, AWS, Azure, etc.)
