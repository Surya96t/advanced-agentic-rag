# Phase 7: Frontend Implementation Plan

> **📖 HOW TO USE THIS DOCUMENT**
>
> This document provides a **detailed frontend roadmap** with checkpoint-by-checkpoint breakdown.
>
> - **Frontend-specific** implementation strategy
> - **Checkpoint goals** and deliverables
> - **Git strategy** (branches, PRs)
> - **Architecture decisions** and technical rationale
>
> **For overall project status and remaining tasks, see:**
>
> - `../PROJECT_STATUS.md` (root) - Single source of truth for current status

---

**Integration Forge Frontend** - Next.js 16.1.4 with BFF Architecture

**Status:** Checkpoints 1-4 Complete ✅ | Checkpoint 5 In Progress 🚧

---

## 🎯 Project Overview

**Current Setup:**

- ✅ Next.js 16.1.4 with App Router
- ✅ React 19.2.3
- ✅ TypeScript 5.x (strict mode)
- ✅ Tailwind CSS 4.x (Oxide engine)
- ✅ shadcn/ui v2 (New York style, RSC-ready)
- ✅ Package manager: pnpm
- ✅ Clerk Authentication integrated
- ✅ Dark mode with next-themes
- ✅ shadcn sidebar-07 navigation

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

### **Checkpoint 1: BFF Foundation & Clerk Auth** ✅ COMPLETE

**Goal:** Set up authentication and proxy layer to FastAPI backend

**Completed Tasks:**

1. ✅ Installed dependencies: `@clerk/nextjs`, `zustand`
2. ✅ Configured environment variables (Clerk keys, FastAPI URL)
3. ✅ Created Clerk middleware for route protection
4. ✅ Updated root layout with `ClerkProvider`
5. ✅ Built BFF Route Handlers (`app/api/health`, `app/api/documents`, `app/api/chat`)
6. ✅ Created API client utility for forwarding requests with JWT tokens
7. ✅ Built sign-in/sign-up pages with Clerk components
8. ✅ Created dashboard layout with shadcn sidebar-07 navigation, dark mode, profile dropdown

**Delivered:**

- ✅ Clerk authentication flows working
- ✅ Protected routes redirect to sign-in
- ✅ BFF health check proxies to FastAPI
- ✅ JWT tokens automatically forwarded to backend
- ✅ Modern dashboard with collapsible sidebar, theme toggle, user profile dropdown

**PR:** #7 - Frontend Foundation & BFF Setup

---

### **Checkpoint 2: Document Upload UI** ✅ COMPLETE

**Goal:** Build document management with drag-and-drop upload

**Completed Tasks:**

1. ✅ Installed shadcn components: `dialog`, `progress`, `badge`, `scroll-area`, `sonner`, `table`
2. ✅ Created unified documents page (Server Component + Client Component)
3. ✅ Built file upload component with HTML5 drag-and-drop
4. ✅ Implemented file validation (PDF, MD, TXT, max 10MB)
5. ✅ Added progress bar during upload (with indeterminate state)
6. ✅ Created responsive document list (table + mobile cards with Skeleton loading)
7. ✅ Built delete confirmation dialog with bulk delete
8. ✅ Implemented BFF route handlers for documents (GET, POST, DELETE)
9. ✅ Added search, sort, and filtering capabilities
10. ✅ Integrated toast notifications for feedback (sonner)

**Delivered:**

- ✅ Drag-and-drop file upload working
- ✅ Real-time upload progress display
- ✅ Document list with Skeleton loading states
- ✅ Delete documents with confirmation (single + bulk)
- ✅ Toast notifications for success/error
- ✅ Empty state when no documents
- ✅ Mobile-responsive design (cards on mobile, table on desktop)

**PR:** #9 - Document Upload & Management UI

---

### **Checkpoint 3: Chat Interface + SSE Streaming** ✅ COMPLETE

**Goal:** Build chat UI with real-time SSE streaming responses

**Completed Tasks:**

1. ✅ Installed dependencies: `react-markdown`, `remark-gfm`, `rehype-highlight`
2. ✅ Installed shadcn components: `textarea`, `scroll-area`, `avatar`
3. ✅ Created chat page with SSE streaming (Server + Client Components)
4. ✅ Built message components (user/AI bubbles, markdown rendering)
5. ✅ Created message input with auto-resize textarea
6. ✅ Implemented `useChat` hook with Zustand for state management
7. ✅ Built BFF route handler for SSE streaming chat
8. ✅ Added markdown rendering with syntax highlighting
9. ✅ Created citation component with progressive display
10. ✅ Implemented auto-scroll to latest message
11. ✅ Added SSE client utility with typed event parser
12. ✅ Implemented event handlers: `agent_start`, `progress`, `citation`, `token`, `validation`, `end`
13. ✅ Built agent status indicators (Router → Expander → Retriever → Generator → Validator)
14. ✅ Added typing indicator animation
15. ✅ Implemented error recovery, retry logic, and stream cancellation

**Delivered:**

- ✅ Send messages and receive AI responses
- ✅ Real-time token-by-token streaming
- ✅ Markdown formatting in messages
- ✅ Citations displayed progressively as badges
- ✅ Auto-scroll to bottom on new messages
- ✅ Textarea auto-resizes as user types
- ✅ Agent status indicators update in real-time
- ✅ Graceful error handling with retry and XSS protection
- ✅ Stream cancellation (stop generation button)

**PR:** #7 - Frontend Foundation with SSE Streaming  
**Note:** Checkpoints 3 & 4 were combined in implementation

---

### **Checkpoint 5: Polish & Deployment** 🚧 IN PROGRESS

**Goal:** Production-ready polish and error handling

**Completed Tasks:**

1. ✅ Created error pages (global error.tsx, 404 not-found.tsx)
2. ✅ Displayed rate limit with RateLimitBanner component
3. ✅ Added loading states with Skeleton components (documents page)
4. ✅ Ensured mobile-responsive design (documents cards, responsive nav)
5. ✅ Added ARIA labels and keyboard navigation (team switcher shortcuts)
6. ✅ Fixed backend document deletion endpoint
7. ✅ Implemented useIsMobile SSR handling
8. ✅ Converted navigation to Next.js Link components

**Remaining Tasks:**

3. ⏳ Implement Suspense boundaries throughout
4. ⏳ Add specific error pages (401, 429, 500)
5. ⏳ Implement code splitting with dynamic imports
6. ⏳ Add image optimization (already using Next.js Image)
7. ⏳ Run bundle analysis
8. ⏳ End-to-end testing with backend

**Delivered So Far:**

- ✅ Works on mobile/tablet/desktop
- ✅ Loading states (Skeleton components)
- ✅ Toast notifications for feedback
- ✅ Rate limit display with banner
- ✅ Custom error pages (global + 404)
- ✅ Keyboard navigation (Cmd/Ctrl + 1-9 for teams)
- ⏳ Accessible to screen readers (partial)
- ⏳ Fast page loads (<2s) (needs verification)
- ⏳ All error states handled gracefully (needs specific error pages)
- ⏳ Ready for deployment (needs final testing)

**PR:** #11 - Production Polish & Deployment Prep (IN PROGRESS)

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

- ✅ Checkpoint 1: Branch `frontend` (from `main`) - MERGED
- ✅ Checkpoint 2: Branch `feat/upload-ui` (from `frontend`) - MERGED as PR #9
- 🚧 Checkpoint 3-5: Branch `feat/chat-basic` (from `frontend`) - IN PROGRESS
- ~~Checkpoint 4: Branch `feat/sse-streaming`~~ - COMBINED WITH CHECKPOINT 3
- Checkpoint 5: Polish continues on `feat/chat-basic` or new `feat/ui-polish` branch

**Pull Requests:**

- ✅ PR #7: Frontend Foundation & BFF Setup - MERGED
- ✅ PR #8: Code cleanup - MERGED
- ✅ PR #9: Document Upload & Management UI - MERGED
- ~~PR #10: SSE Streaming Integration~~ - COMBINED WITH PR #7
- 🚧 PR #11: Production Polish & Deployment Prep - IN PROGRESS

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
