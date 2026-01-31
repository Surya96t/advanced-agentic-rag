# Phase 7: Frontend Implementation Plan

**Integration Forge Frontend** - Next.js 16.1.4 with BFF Architecture

---

## 🎯 Project Overview

**Current Setup:**

- ✅ Next.js 16.1.4 with App Router
- ✅ React 19.2.3
- ✅ TypeScript 5.x (strict mode)
- ✅ Tailwind CSS 4.x (Oxide engine)
- ✅ shadcn/ui v2 (New York style, RSC-ready)
- ✅ Package manager: pnpm

**Architecture Pattern:** BFF (Backend-for-Frontend)

```
Browser → Next.js Route Handlers → FastAPI Backend
  (UI)      (BFF Proxy Layer)       (Agentic RAG)
```

**Backend API Available:**

- Base URL: `http://localhost:8000`
- Authentication: JWT Bearer tokens (Clerk)
- Endpoints: `/health`, `/api/v1/documents`, `/api/v1/chat`, `/api/v1/ingest`
- Rate Limits: Ingest (20/hr), Chat (100/hr), Documents (200/hr)

---

## 📋 Implementation Checkpoints

### **Checkpoint 1: BFF Foundation & Clerk Auth** (6-8 hours)

**Goal:** Set up authentication and proxy layer to FastAPI backend

**Tasks:**

1. Install dependencies: `@clerk/nextjs`, `zustand`
2. Configure environment variables (Clerk keys, FastAPI URL)
3. Create Clerk middleware for route protection
4. Update root layout with `ClerkProvider`
5. Build BFF Route Handlers (`app/api/health`, `app/api/documents`, `app/api/chat`)
6. Create API client utility for forwarding requests with JWT tokens
7. Build sign-in/sign-up pages with Clerk components
8. Create dashboard layout with navigation and user button

**Deliverables:**

- Clerk authentication flows working
- Protected routes redirect to sign-in
- BFF health check proxies to FastAPI
- JWT tokens automatically forwarded to backend
- Dashboard layout with navigation

---

### **Checkpoint 2: Document Upload UI** (8-10 hours)

**Goal:** Build document management with drag-and-drop upload

**Tasks:**

1. Install shadcn components: `dialog`, `progress`, `badge`, `scroll-area`, `sonner`, `table`
2. Create upload page (Server Component wrapper)
3. Build file upload component (Client Component with HTML5 drag-and-drop)
4. Implement file validation (PDF, MD, TXT, max 10MB)
5. Add progress bar during upload
6. Create document list component (Server Component with table)
7. Build delete confirmation dialog
8. Implement BFF route handlers for documents (GET, POST, DELETE)
9. Add Zustand store for upload state management
10. Implement toast notifications for feedback

**Deliverables:**

- Drag-and-drop file upload working
- Real-time upload progress display
- Document list loads server-side (zero JS)
- Delete documents with confirmation
- Toast notifications for success/error
- Empty state when no documents

---

### **Checkpoint 3: Chat Interface (Non-Streaming)** (8-10 hours)

**Goal:** Build basic chat UI with JSON responses

**Tasks:**

1. Install dependencies: `react-markdown`, `remark-gfm`, `rehype-highlight`
2. Install shadcn components: `textarea`, `scroll-area`, `avatar`
3. Create chat page (Server Component layout)
4. Build message components (user and AI message bubbles)
5. Create message input with auto-resize textarea
6. Implement custom `useChat` hook with Zustand
7. Build BFF route handler for chat (POST, non-streaming)
8. Add markdown rendering for AI responses
9. Create citation component (badges with document links)
10. Implement auto-scroll to latest message

**Deliverables:**

- Send message and receive AI response (JSON)
- Markdown formatting in messages
- Citations displayed as badges
- Auto-scroll to bottom on new messages
- Textarea auto-resizes as user types

---

### **Checkpoint 4: SSE Streaming** (10-12 hours)

**Goal:** Real-time streaming AI responses with Server-Sent Events

**Tasks:**

1. Create SSE client utility with typed event parser
2. Build streaming BFF route handler (uses Next.js `ReadableStream`)
3. Update chat hook to support streaming mode
4. Create streaming message component with progressive rendering
5. Implement event handlers: `agent_start`, `progress`, `citation`, `token`, `validation`, `end`
6. Add agent status indicators (Router → Expander → Retriever → Generator → Validator)
7. Build typing indicator animation
8. Implement progressive citation display
9. Add error recovery and reconnection logic

**Deliverables:**

- Messages stream token-by-token
- All SSE events handled correctly
- Citations appear progressively
- Agent status indicators update in real-time
- Graceful error handling with retry

---

### **Checkpoint 5: Polish & Deployment** (6-8 hours)

**Goal:** Production-ready polish and error handling

**Tasks:**

1. Create error pages (401, 429, 500)
2. Display rate limit remaining (from X-RateLimit-Remaining header)
3. Add loading states with Skeleton components
4. Implement Suspense boundaries throughout
5. Ensure mobile-responsive design (mobile-first)
6. Add ARIA labels and keyboard navigation
7. Implement code splitting with dynamic imports
8. Add image optimization
9. Run bundle analysis
10. End-to-end testing with backend

**Deliverables:**

- Works on mobile/tablet/desktop
- Accessible to screen readers
- Fast page loads (<2s)
- All error states handled gracefully
- Rate limit display working
- Ready for deployment

---

## 🚀 Success Criteria

**Authentication:**

- ✅ Sign-in/sign-up flows work seamlessly
- ✅ Protected routes enforce authentication
- ✅ JWT tokens automatically attached to backend requests

**Document Management:**

- ✅ Upload PDF, Markdown, and TXT files
- ✅ Real-time upload progress tracking
- ✅ Document list loads server-side (check HTML source)
- ✅ Delete documents with confirmation

**Chat Interface:**

- ✅ Send messages and receive AI responses
- ✅ Streaming responses with token-by-token display
- ✅ Citations link to source documents
- ✅ Agent status indicators show workflow progress

**User Experience:**

- ✅ Mobile-responsive design
- ✅ Loading states and error handling
- ✅ Toast notifications for feedback
- ✅ Rate limit display
- ✅ Accessible (WCAG 2.1 AA)

---

## 📦 Git Strategy

**Branching:**

- Checkpoint 1: Branch `frontend` (from `main`)
- Checkpoint 2: Branch `feat/upload-ui` (from `frontend`)
- Checkpoint 3: Branch `feat/chat-basic` (from `frontend`)
- Checkpoint 4: Branch `feat/sse-streaming` (from `frontend`)
- Checkpoint 5: Polish on `frontend` branch

**Pull Requests:**

- PR #7: Frontend Foundation & BFF Setup
- PR #8: Document Upload & Management UI
- PR #9: Basic Chat Interface (Non-Streaming)
- PR #10: SSE Streaming Integration
- PR #11: Production Polish & Deployment Prep

---

## 🔑 Key Technical Decisions

**BFF Pattern:**

- All backend requests go through Next.js Route Handlers
- Eliminates CORS issues (single origin)
- Centralized JWT token injection
- Type-safe API contracts

**Server vs Client Components:**

- Server Components by default (zero client JS)
- Client Components only for interactivity (chat input, file upload)
- Suspense boundaries for async data loading

**State Management:**

- Zustand for client state (upload progress, messages)
- Server Actions for mutations with revalidation
- No React Query needed (Server Components + Suspense)

**Streaming Strategy:**

- Non-streaming first (simpler, easier to debug)
- Add SSE streaming in Checkpoint 4
- Progressive enhancement approach

---

## ⏱️ Estimated Timeline

- **Checkpoint 1:** 6-8 hours
- **Checkpoint 2:** 8-10 hours
- **Checkpoint 3:** 8-10 hours
- **Checkpoint 4:** 10-12 hours
- **Checkpoint 5:** 6-8 hours

**Total:** 38-48 hours (~1-2 weeks for one developer)

---

_Ready to start Checkpoint 1! 🚀_
