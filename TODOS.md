# Frontend Implementation TODO

> **⚠️ DEPRECATED - February 1, 2026**
>
> This file is no longer actively maintained. It was used during initial frontend planning but is now outdated.
>
> **Please use instead:**
>
> - **`PROJECT_STATUS.md`** (root) - Current project status and remaining tasks
> - **`frontend/IMPLEMENTATION_PLAN.md`** - Frontend roadmap and checkpoint details
>
> This file is kept for historical reference only.

---

## Project Overview

**Integration Forge Frontend** - A production-grade Next.js 16.1.4+ application using the BFF (Backend-for-Frontend) pattern to provide a conversational RAG interface for API documentation synthesis.

**Tech Stack:**

- **Framework:** Next.js 16.1.4+ (App Router, React Server Components, Turbopack)
- **Language:** TypeScript 5.1+ (strict mode, incremental type checking)
- **Styling:** Tailwind CSS 4.1.18+ (latest version, Oxide engine)
- **UI Components:** shadcn/ui v2+ (Radix UI primitives)
- **Authentication:** Clerk (JWT tokens)
- **Architecture:** BFF Pattern (Route Handlers as proxy layer)
- **Real-time:** SSE (Server-Sent Events) for AI streaming
- **Data Fetching:** `async` Server Components, `use` hook, Suspense streaming

**Core Features:**

- Route Handlers (`app/api/`) proxy all FastAPI requests
- Clerk authentication with server-side JWT extraction
- Server Components for data loading (zero client JS by default)
- Client Components only for interactivity (chat input, upload)
- SSE streaming for real-time AI agent responses
- shadcn/ui v2 components with copy-paste architecture
- Mobile-first responsive design
- Type-safe routing with `PageProps<'/path'>` and `RouteContext<'/path'>`

**BFF Architecture:**

```
Browser → Next.js Route Handlers → FastAPI Backend
  (UI)      (BFF Proxy Layer)       (Agentic RAG)
```

**BFF Benefits:**

- Single origin (eliminates CORS)
- Centralized JWT forwarding
- Request/response transformation
- Error normalization for frontend
- Type-safe API contracts
- Future: Edge caching, rate limiting, observability

---

## Git Branching Strategy

### Current Branch: `frontend`

**Starting Point:** Branch from `main` after Phase 6 (Authentication & Security) merged  
**Approach:** Feature-based checkpoints with incremental PRs  
**Timeline:** 3-4 weeks (40-60 hours total)

### Checkpoint 1: Project Setup & BFF Foundation ⬅️ START HERE

**Branch:** `frontend`  
**Effort:** 6-8 hours

**Deliverables:**

- Next.js 16.1.4+ initialized with App Router and Turbopack
- TypeScript strict mode with auto-generated type helpers
- Tailwind CSS + shadcn/ui v2 configured
- Clerk authentication integrated (server-side `auth()`)
- BFF Route Handler structure (`app/api/`)
- Root layout with `ClerkProvider` and theme provider
- Environment variables configured (.env.local + .env.example)

**shadcn/ui Components to Install:**

```bash
npx shadcn@latest add button card input skeleton
```

**Success Criteria:**

✅ App runs on localhost:3000 with Turbopack  
✅ Clerk sign-in/sign-up flows working  
✅ BFF health check (`GET /api/health`) proxies to FastAPI  
✅ shadcn/ui Button renders correctly  
✅ Type checking passes (`next dev`, `next build`, or `next typegen`)

**Goal:** Auth + BFF foundation ready for development  
**PR:** #7 - Frontend Foundation & BFF Setup

### Checkpoint 2: Document Upload & Management UI

**Branch:** `feat/upload-ui`  
**Effort:** 8-10 hours

**Deliverables:**

- Upload page (`app/(dashboard)/upload/page.tsx`) - Server Component wrapper
- BFF Route Handlers:
  - `GET/POST app/api/documents/route.ts` (list & ingest proxy)
  - `DELETE app/api/documents/[id]/route.ts` (delete proxy)
- Document list Server Component with `Suspense` boundary
- File upload Client Component with HTML5 drag-and-drop
- Delete confirmation Dialog

**shadcn/ui Components to Install:**

```bash
npx shadcn@latest add dialog progress badge separator scroll-area sonner
```

**Features:**

- **Drag-and-drop upload** - Native HTML5 File API (no library needed)
- **File validation** - PDF, Markdown, TXT, max 10MB, client-side checks
- **Upload progress** - shadcn `Progress` component with real-time percentage
- **Document list** - Server Component fetches via BFF on initial load
- **Delete with confirmation** - shadcn `Dialog` before deletion
- **Empty state** - Friendly message when no documents uploaded
- **Toast notifications** - shadcn `Sonner` for success/error feedback

**Data Flow:**

1. Server Component fetches documents on page load (zero JS!)
2. Client Component handles file upload interactions
3. BFF forwards multipart/form-data to FastAPI `/api/v1/ingest`
4. Optimistic UI updates on delete, revalidates via Server Action

**Success Criteria:**

✅ Upload PDF/Markdown/TXT files with progress bar  
✅ Document list loads server-side (check View Source - no client fetch)  
✅ Delete document with confirmation dialog  
✅ Empty state shows when no documents  
✅ Toast notifications for upload success/failure

**Goal:** Users can upload and manage API documentation  
**PR:** #8 - Document Upload & Management UI

---

### Checkpoint 3: Chat Interface (Non-Streaming First)

**Branch:** `feat/chat-basic`  
**Effort:** 8-10 hours

**Deliverables:**

- Chat page (`app/(dashboard)/chat/page.tsx`) - Server Component layout
- BFF Route Handler: `POST app/api/chat/route.ts` (non-streaming JSON)
- Message components (Client Components for interactivity)
- Custom `useChat` hook for state management

**shadcn/ui Components to Install:**

```bash
npx shadcn@latest add textarea scroll-area avatar
```

**Features:**

- **Message input** - shadcn `Textarea` with auto-resize (dynamically expand as user types)
- **Message list** - shadcn `ScrollArea` with auto-scroll to bottom on new messages
- **Non-streaming responses** - Start with JSON responses (simpler, then add streaming in Checkpoint 4)
- **Citation display** - Inline links to source documents with document name badges
- **Markdown rendering** - Use `react-markdown` for formatted AI responses
- **User/AI avatars** - shadcn `Avatar` component for visual distinction

**Data Flow:**

1. User submits message via Client Component
2. Client calls `POST /api/chat` (BFF Route Handler)
3. BFF forwards to `POST /api/v1/chat` (FastAPI, non-streaming)
4. BFF returns JSON response with content + citations
5. Client renders new message in chat UI

**Message UI:**

- **User messages:** Right-aligned, primary color background
- **AI messages:** Left-aligned, muted background, with citations below
- **Citations:** Small badge components linking to source documents

**Success Criteria:**

✅ Send message and receive AI response  
✅ Messages render with Markdown formatting  
✅ Citations link to source documents  
✅ Auto-scroll to bottom on new messages  
✅ Textarea auto-resizes as user types

**Goal:** Basic chat working (non-streaming baseline)  
**PR:** #9 - Basic Chat Interface (Non-Streaming)

---

### Checkpoint 4: SSE Streaming & Conversational AI UX

**Branch:** `feat/sse-streaming`  
**Effort:** 10-12 hours

**Deliverables:**

- BFF streaming Route Handler: `POST app/api/chat/stream/route.ts` (SSE)
- SSE client utility (`lib/sse-client.ts`) with typed event parsing
- Streaming message renderer (accumulates tokens in real-time)
- Agent status indicator component

**shadcn/ui Components to Install:**

```bash
npx shadcn@latest add spinner badge
```

**Conversational Features:**

- **Real-time streaming** - Token-by-token message rendering as AI generates response
- **Agent status indicators** - Visual badges showing: `routing → retrieving → generating → validating`
- **Typing indicator** - Animated dots (shadcn `Spinner`) while waiting for first token
- **Inline citations** - Citations appear during streaming as `Citation` events arrive
- **Smooth animations** - Messages fade in, scroll auto-follows stream

**SSE Event Types (from FastAPI):**

- `AgentStart` - Agent begins processing
- `Progress` - Status updates (routing, retrieving, generating, validating)
- `Citation` - Source document reference
- `Token` - AI-generated text chunk
- `Validation` - Quality score and validation result
- `End` - Stream complete

**Data Flow:**

1. User submits message
2. Client calls `POST /api/chat/stream` (BFF Route Handler)
3. BFF forwards to `POST /api/v1/chat?stream=true` (FastAPI SSE)
4. BFF streams SSE events to client (keeps connection open)
5. Client parses events and updates UI in real-time

**Technical Implementation:**

- Use native `fetch` with `ReadableStream` (no `EventSource` needed)
- Parse SSE format: `data: {...}\n\n`
- AbortController for stream cancellation (user can stop generation)
- Accumulate tokens in state, render incrementally

**Success Criteria:**

✅ Messages stream token-by-token in real-time  
✅ Agent status badge updates during processing  
✅ Citations appear as stream progresses  
✅ Typing indicator shows before first token  
✅ User can cancel ongoing generation  
✅ Smooth scroll-to-bottom during streaming

**Goal:** Production-quality conversational AI experience  
**PR:** #10 - SSE Streaming & Agent Status UI

---

### Checkpoint 5: Error Handling, Rate Limits & UI Polish

**Branch:** `feat/ui-polish`  
**Effort:** 8-10 hours

**Deliverables:**

- React Error Boundary components (route-level and component-level)
- Rate limit UI (banner with countdown timer)
- Loading skeletons for all async states
- Toast notification system (success, error, info)
- Comprehensive error handling in BFF and client

**shadcn/ui Components to Install:**

```bash
npx shadcn@latest add alert skeleton
```

_(Sonner already installed in Checkpoint 2)_

**Features:**

**Rate Limit Handling:**

- Detect 429 responses in BFF Route Handlers
- Parse `X-RateLimit-Remaining`, `X-RateLimit-Reset` headers from FastAPI
- Display shadcn `Alert` banner with countdown timer
- Disable chat input until rate limit resets
- Show remaining quota in header (optional)

**Error Handling Strategy:**

- **Network Errors:** Auto-retry with exponential backoff (3 attempts)
- **401 Unauthorized:** Clerk middleware redirects to sign-in automatically
- **403 Forbidden:** Show "Permission denied" Alert
- **429 Rate Limited:** Show Alert banner with countdown timer
- **422 Validation Error:** Show field-specific error messages inline
- **500 Server Error:** Show generic error Alert + retry button
- **SSE Connection Lost:** Auto-reconnect with exponential backoff

**Loading States:**

- shadcn `Skeleton` for document list while loading
- shadcn `Skeleton` for chat history (if implemented)
- shadcn `Spinner` for message sending/streaming
- Disable buttons during async operations

**Toast Notifications (Sonner):**

- **Success:** "Document uploaded successfully"
- **Error:** "Failed to upload document"
- **Info:** "Reconnecting to chat..."
- **Warning:** "Approaching rate limit"

**Responsive Design Refinements:**

- Mobile-first breakpoints (320px, 640px, 768px, 1024px, 1280px)
- Touch-friendly buttons (minimum 44x44px)
- Collapsible sidebar on mobile (if sidebar added)
- Optimized layout for tablet and desktop

**Accessibility:**

- ARIA labels on all interactive elements
- Keyboard navigation (Tab, Enter, Escape, Arrow keys)
- Focus indicators (Tailwind `focus-visible:` variants)
- Screen reader announcements for dynamic content (live regions)
- Color contrast WCAG AA compliant (built into shadcn/ui)

**Success Criteria:**

✅ Rate limit banner displays with accurate countdown  
✅ Network errors auto-retry with backoff  
✅ Loading skeletons show during data fetching  
✅ Toast notifications for all user actions  
✅ Error boundaries catch React errors gracefully  
✅ App is fully keyboard navigable  
✅ Responsive on mobile, tablet, and desktop

**Goal:** Production-ready UX with polished error handling  
**PR:** #11 - Error Handling, Rate Limits & Polish

---

### Checkpoint 6: Conversation History (Optional) 🎯

**Branch:** `feat/conversation-history`  
**Effort:** 10-12 hours  
**Status:** Optional (Week 2-3)

**⚠️ Backend Changes Required:**

This feature requires new backend endpoints and database tables. Coordinate with backend team.

**New Backend Requirements:**

- Database tables: `conversations`, `messages`
- Endpoints:
  - `GET /api/v1/conversations` - List user's conversations
  - `GET /api/v1/conversations/{id}` - Get conversation with messages
  - `POST /api/v1/conversations` - Create new conversation
  - `DELETE /api/v1/conversations/{id}` - Delete conversation

**Frontend Deliverables:**

- Conversation sidebar component (Client Component with server-fetched data)
- BFF Route Handlers:
  - `GET/POST app/api/conversations/route.ts`
  - `GET/DELETE app/api/conversations/[id]/route.ts`
- Conversation list Server Component
- Resume conversation logic in chat page

**shadcn/ui Components to Install:**

```bash
npx shadcn@latest add sidebar
```

_(scroll-area, button already installed)_

**Features:**

- **Conversation sidebar** - shadcn `Sidebar` component with conversation list
- **Auto-save conversations** - Save messages as user chats (debounced)
- **Resume conversations** - Click past conversation to restore context
- **Search/filter** - Find conversations by keyword or date
- **Delete conversations** - Confirmation dialog before deletion
- **Conversation metadata** - Title (auto-generated from first message), timestamp, message count

**Data Flow:**

1. Server Component fetches conversation list on page load
2. Client Component handles sidebar interactions (open, close, select)
3. Selecting conversation loads messages via BFF Route Handler
4. Chat state updates with historical messages

**Success Criteria:**

✅ Sidebar shows list of past conversations  
✅ Click conversation to resume chat  
✅ Auto-save new messages to conversation  
✅ Delete conversation with confirmation  
✅ Search/filter conversations

**Goal:** Persistent conversation history for users  
**PR:** #12 - Conversation History (Optional)

---

### Checkpoint 7: Feedback & Follow-up Suggestions (Optional) 🎯

**Branch:** `feat/feedback`  
**Effort:** 6-8 hours  
**Status:** Optional (Week 3)

**⚠️ Backend Changes Required:**

This feature requires a new feedback endpoint. Coordinate with backend team.

**New Backend Requirements:**

- Database table: `feedback` (likely already exists - check backend schema)
- Endpoint:
  - `POST /api/v1/feedback` - Submit user feedback
  - Expected schema: `{ message_id: str, rating: int, comment?: str }`

**Frontend Deliverables:**

- Feedback component (thumbs up/down on AI messages)
- BFF Route Handler: `POST app/api/feedback/route.ts`
- Feedback modal for optional comments
- Follow-up suggestions (if backend provides them)

**shadcn/ui Components to Install:**

```bash
npx shadcn@latest add toggle
```

_(dialog already installed)_

**Features:**

- **Thumbs up/down** - shadcn `Toggle` component on each AI message
- **Feedback modal** - Optional comment field when user downvotes (shadcn `Dialog`)
- **Feedback submission** - POST to BFF route, which forwards to FastAPI
- **Follow-up suggestions** - Display suggested questions after AI response (if backend provides)
- **Visual feedback** - Toast notification on successful submission

**Data Flow:**

1. User clicks thumbs up/down on AI message
2. If thumbs down, show Dialog for optional comment
3. Client calls `POST /api/feedback` (BFF Route Handler)
4. BFF forwards to `POST /api/v1/feedback` (FastAPI)
5. Show success toast, disable feedback buttons for that message

**Follow-up Suggestions (if backend supports):**

- Backend generates 2-3 suggested follow-up questions
- Display as clickable chips/buttons below AI message
- Clicking suggestion auto-populates chat input

**Success Criteria:**

✅ Thumbs up/down buttons render on AI messages  
✅ Feedback modal shows on thumbs down  
✅ Feedback submits successfully to backend  
✅ Follow-up suggestions display (if available)  
✅ Toast notification confirms submission

**Goal:** Collect user feedback to improve RAG quality  
**PR:** #13 - Feedback & Suggestions (Optional)

---

### Checkpoint 8: Testing & Documentation

**Branch:** `feat/testing`  
**Effort:** 10-12 hours

**Deliverables:**

- Vitest configuration for unit tests
- Playwright configuration for E2E tests
- Component tests (React Testing Library)
- BFF Route Handler tests
- E2E user flow tests
- Testing documentation

**Testing Stack:**

- **Unit Tests:** Vitest + React Testing Library
- **Integration Tests:** Vitest with mocked FastAPI responses
- **E2E Tests:** Playwright for full user flows

**Test Coverage:**

**Unit Tests (Components):**

- Message rendering (user/AI messages, Markdown, citations)
- File upload component (validation, progress, errors)
- Document list (empty state, delete confirmation)
- Error boundary (fallback UI)
- Loading skeletons

**Integration Tests (BFF Route Handlers):**

- `GET /api/documents` - Returns user documents
- `POST /api/ingest` - Forwards multipart/form-data to FastAPI
- `DELETE /api/documents/{id}` - Deletes document
- `POST /api/chat` - Returns AI response (non-streaming)
- `POST /api/chat/stream` - Streams SSE events
- Error handling (401, 429, 500 responses)

**E2E Tests (Playwright):**

- **Auth Flow:** Sign up → Sign in → Sign out
- **Upload Flow:** Upload document → View document list → Delete document
- **Chat Flow (Non-Streaming):** Send message → Receive response → View citations
- **Chat Flow (Streaming):** Send message → See typing indicator → Stream tokens → See citations
- **Error Flow:** Trigger rate limit → See banner → Wait for reset
- **Responsive:** Test on mobile, tablet, desktop viewports

**Success Criteria:**

✅ Unit test coverage >80% for components  
✅ Integration tests for all BFF routes  
✅ E2E tests for critical user flows  
✅ CI/CD pipeline runs tests on PR  
✅ Test documentation in `README.md`

**Goal:** Comprehensive test coverage for production readiness  
**PR:** #14 - Testing Suite & Documentation

---

## Phase 9: Frontend Implementation Plan

### 9.1: Project Setup & Configuration (Checkpoint 1)

- [ ] **Initialize Next.js 16.1.4+ Project**
  - Run `npx create-next-app@latest` with flags:
    - App Router: Yes
    - TypeScript: Yes
    - Tailwind CSS: Yes
    - ESLint: Yes
    - `src/` directory: Optional (use `app/` at root)
    - App Router: Yes (recommended)
    - Turbopack: Yes (default in 16.1.4+)
    - Import alias: `@/*` (default)
  - Folder structure:
    - `app/` - Routes and layouts (file-system routing)
    - `components/` - Reusable UI components (shadcn/ui installed here)
    - `lib/` - Utilities (BFF client, SSE client, utils)
    - `types/` - TypeScript types (API contracts, shared types)
    - `hooks/` - Custom React hooks (useChat, useUpload)
  - Configure path aliases in `tsconfig.json`: `"@/*": ["./*"]`

- [ ] **TypeScript Configuration** (`tsconfig.json`)
  - Enable strict mode: `"strict": true`
  - Enable incremental type checking: `"incremental": true`
  - Additional strict checks:
    - `"noUncheckedIndexedAccess": true` (safer array access)
    - `"noUnusedLocals": true` (catch unused variables)
    - `"noUnusedParameters": true` (catch unused function parameters)
  - Note: `PageProps` and `RouteContext` type helpers are auto-generated during `next dev`, `next build`, or `next typegen`

- [ ] **Install Core Dependencies**
  - Core: Next.js 16.1+, React 19+, TypeScript 5.1+
  - Styling: `tailwindcss@4.1.18` (latest, Oxide engine), `@tailwindcss/vite`
  - Auth: `@clerk/nextjs@latest`
  - UI: shadcn/ui will install Radix UI primitives automatically
  - Utilities: `clsx`, `tailwind-merge`, `lucide-react` (for icons)
  - Dev: `@types/node`, `@types/react`, `@types/react-dom`

- [ ] **Configure shadcn/ui v2**
  - Run `npx shadcn@latest init` (creates `components.json` config file)
  - Select style: Default (or New York for more modern aesthetic)
  - Select base color: Slate (or customize to match brand)
  - Configure CSS variables: Yes (enables easy theming)
  - Set path aliases: `@/components`, `@/lib/utils`
  - Install initial components needed for setup phase: `button`, `card`, `input`, `skeleton`
  - Verify `components/ui/` folder created with components
  - Verify `lib/utils.ts` created with `cn()` helper function

- [ ] **Environment Configuration**
  - Create `.env.local` (gitignored, contains secrets)
  - Add Clerk authentication keys (from Clerk dashboard)
  - Add backend API URL (for BFF to forward requests)
  - Add Clerk redirect URLs for sign-in/sign-up flows
  - Add after-authentication redirect URLs
  - Create `.env.example` (committed to repo, no secrets)
  - Use same structure as `.env.local` but with placeholder values
  - Add comments explaining each variable's purpose

- [ ] **Linting & Formatting**
  - ESLint: Already configured by `create-next-app`
  - Optional: Install Prettier for consistent code formatting
  - Optional: Install `prettier-plugin-tailwindcss` for class sorting
  - Create `.prettierrc` config file with preferences (semi, quotes, tabs, trailing commas)

- [ ] **Verify Setup**
  - Run `npm run dev` (should start on `localhost:3000` with Turbopack bundler)
  - Visit `http://localhost:3000` (should see default Next.js welcome page)
  - Run `npm run build` (should compile successfully without errors)
  - Run `npm run lint` (should pass with no linting errors)

---

### 9.2: BFF (Backend-for-Frontend) Architecture (Checkpoint 1)

**Core Principle:** Next.js Route Handlers (`app/api/`) act as a **proxy layer** between frontend and FastAPI backend.

**Why BFF?**

- **Eliminates CORS** - Same-origin requests from browser
- **Centralized Auth** - Extract JWT from Clerk server-side, forward to FastAPI
- **Error Normalization** - Transform backend errors into user-friendly messages
- **Type Safety** - Share TypeScript types between frontend and BFF
- **Future-Proof** - Add caching, rate limiting, analytics without touching frontend

- [ ] **Create BFF Utility** (`lib/bff-client.ts`)
  - Purpose: Centralized fetch wrapper for server-side BFF → FastAPI calls
  - Install `server-only` package to prevent client-side usage
  - Import `server-only` at top of file
  - Create type-safe fetch wrapper with:
    - Automatic JWT extraction from Clerk `auth()`
    - Error handling with typed error responses
    - Retry logic with exponential backoff (3 attempts max)
    - Request/response logging (development only)

- [ ] **BFF Route Handler Structure** (`app/api/`)
  - All routes use Next.js Route Handlers (Web Request/Response APIs)
  - Follow naming convention:
    - `app/api/documents/route.ts` - List/create documents
    - `app/api/documents/[id]/route.ts` - Get/update/delete document
    - `app/api/chat/route.ts` - Non-streaming chat
    - `app/api/chat/stream/route.ts` - Streaming chat (SSE)
    - `app/api/ingest/route.ts` - Document ingestion
  - Use `RouteContext<'/api/documents/[id]'>` for type-safe dynamic params
  - Export HTTP method functions: `GET`, `POST`, `DELETE`, etc.

- [ ] **BFF Health Check Route** (`app/api/health/route.ts`)
  - Purpose: Verify BFF → FastAPI connection
  - Route: `GET /api/health` → `GET /api/v1/health`
  - Return JSON: status OK and backend connected
  - Use this to validate BFF setup before building other features

- [ ] **JWT Token Forwarding**
  - Server-side only (Route Handlers, Server Components)
  - Use `auth()` from `@clerk/nextjs/server` to extract token
  - Add `Authorization: Bearer ${token}` header to all FastAPI requests
  - Handle 401 responses (Clerk middleware auto-redirects unauthenticated users)

- [ ] **Error Transformation in BFF**
  - Catch FastAPI errors and transform for frontend user-friendly messages
  - Transform specific error codes:
    - 401 Unauthorized: Clerk handles redirect automatically
    - 403 Forbidden: Return permission denied error
    - 422 Validation Error: Return validation details
    - 429 Rate Limit: Return retry-after time
    - 500 Server Error: Return generic error message
  - Preserve rate limit headers: `X-RateLimit-Remaining`, `X-RateLimit-Reset`
  - Never expose raw backend errors to frontend (security risk)

- [ ] **Type Safety** (`types/api.ts`)
  - Mirror FastAPI schemas in TypeScript interfaces
  - Define types for:
    - Documents (id, filename, size, upload date)
    - Chat messages (role, content, citations)
    - Citations (document ID, name, text snippet, relevance score)
    - Chat responses (content, citations array, quality score)
    - SSE events (agent_start, progress, citation, token, validation, end)
  - Share types between BFF Route Handlers and frontend components
  - Optional: Use Zod for runtime validation of API responses

- [ ] **CORS Headers (optional, only if needed)**
  - BFF eliminates CORS for browser requests
  - If external clients need access (future), add CORS headers to specific routes
  - Set Allow-Origin, Allow-Methods, Allow-Headers as needed

- [ ] **Verify BFF Setup**
  - Start FastAPI backend on port 8000
  - Start Next.js frontend with `npm run dev`
  - Test health check: visit `http://localhost:3000/api/health`
  - Verify response shows backend connected

---

### 9.3: Authentication with Clerk (Checkpoint 1)

**Key Next.js 16 Pattern:** Server Components for auth checks (no client-side authentication flash), `auth()` returns user session server-side, Middleware protects routes before rendering.

- [ ] **Clerk Setup** (`app/layout.tsx`)
  - Import `ClerkProvider` from `@clerk/nextjs`
  - Wrap entire app with `<ClerkProvider>` in root layout
  - Configure Clerk appearance object (optional: customize colors, fonts, branding)
  - Set localization if needed (default is English)
  - Root layout is a Server Component by default (no 'use client' needed)

- [ ] **Authentication Pages**
  - Create catch-all route: `app/sign-in/[[...sign-in]]/page.tsx`
  - Import and render Clerk's `<SignIn />` component
  - Create catch-all route: `app/sign-up/[[...sign-up]]/page.tsx`
  - Import and render Clerk's `<SignUp />` component
  - These are Client Components (Clerk components require interactivity)

- [ ] **Protected Routes** (`middleware.ts`)
  - Import and export Clerk's `clerkMiddleware` from `@clerk/nextjs/server`
  - Configure public routes array: `/`, `/sign-in`, `/sign-up`
  - All other routes are protected by default
  - Protected routes: `/dashboard`, `/upload`, `/chat`
  - Clerk automatically redirects unauthenticated users to sign-in page
  - Middleware runs before page rendering (no flash of unauthenticated content)

- [ ] **JWT Token Management**
  - Server Components: Use `auth()` from `@clerk/nextjs/server` to get user session
  - Extract JWT token with `await getToken()` for BFF Route Handlers
  - BFF routes: Forward JWT to FastAPI in `Authorization: Bearer {token}` header
  - Client Components: Use `useAuth()` hook from `@clerk/nextjs` (for UI only, not API calls)
  - Never store tokens in localStorage (Clerk handles this securely)

- [ ] **User Context & UI**
  - Import `UserButton` component from `@clerk/nextjs` for user menu
  - Place `<UserButton />` in app header/navbar
  - Shows user avatar, email, and sign-out option
  - Optionally use `useUser()` hook in Client Components for user info display

- [ ] **Verify Clerk Setup**
  - Visit `http://localhost:3000/sign-up`
  - Create test account
  - Verify redirect to `/dashboard` after sign-up
  - Sign out and visit protected route (should redirect to sign-in)
  - Sign in and verify access to protected routes

---

### 9.4: Document Upload & Management (Checkpoint 2)

**Key Next.js 16 Patterns:** Server Component for data fetching (zero client JS for initial load), Client Component only for file upload interactivity, Stream data with `Suspense` and `loading.tsx`.

- [ ] **BFF Routes** (`app/api/documents/`, `app/api/ingest/`)
  - **GET** `/api/documents/route.ts` → Proxy to `GET /api/v1/documents`
    - Extracts JWT from Clerk `auth()`
    - Forwards to FastAPI with Authorization header
    - Returns list of user's uploaded documents
  - **DELETE** `/api/documents/[id]/route.ts` → Proxy to `DELETE /api/v1/documents/{id}`
    - Uses `RouteContext<'/api/documents/[id]'>` for type-safe ID param
    - Deletes specified document for authenticated user
  - **POST** `/api/ingest/route.ts` → Proxy to `POST /api/v1/ingest`
    - Handles multipart/form-data file upload
    - Forwards file to FastAPI for processing
    - Returns document ID and success message

- [ ] **Upload Page** (`app/(dashboard)/upload/page.tsx`)
  - Create Server Component as page wrapper
  - Use `async` function to fetch initial document list
  - Wrap Client Components in `Suspense` boundary
  - Use `PageProps` type helper (auto-generated) for type safety

- [ ] **File Upload Component** (Client Component)
  - Add `'use client'` directive at top
  - Implement drag-and-drop zone with native HTML5 File API (onDragOver, onDrop events)
  - No external library needed (keep bundle small)
  - File validation (client-side):
    - Accepted types: PDF, Markdown (.md), TXT
    - Max file size: 10MB
    - Show validation errors immediately
  - Multiple file upload support (iterate through FileList)
  - Visual states: default, hover (when dragging file over), dropping, uploading, success, error
  - Use shadcn/ui `Progress` component for upload progress bar
  - AbortController to cancel ongoing uploads

- [ ] **Document List** (Server Component)
  - Fetch documents via `GET /api/documents` (BFF route)
  - Render list server-side (no client-side fetch needed)
  - Use shadcn/ui `Card` component for each document item
  - Display document metadata: filename, size, upload date
  - Delete button (triggers Client Component modal)
  - Empty state component when no documents (friendly message, upload prompt)
  - Use `Suspense` boundary with `Skeleton` fallback for loading state

- [ ] **Delete Confirmation** (Client Component)
  - shadcn/ui `Dialog` component for confirmation
  - Show document name in confirmation message
  - Confirm/Cancel buttons
  - On confirm: Call `DELETE /api/documents/{id}` via BFF
  - Optimistic UI update (remove from list immediately)
  - Revalidate server data after deletion (use Server Actions or client-side revalidation)
  - Show toast notification (shadcn/ui `Sonner`) on success/error

- [ ] **Upload Flow**
  1. User drags file or clicks browse button
  2. Client validates file (type, size)
  3. If valid: POST to `/api/ingest` with FormData
  4. Show progress bar (track upload progress)
  5. On success: Show toast, refetch document list
  6. On error: Show toast with error message, allow retry

- [ ] **Verify Upload Feature**
  - Upload PDF document (should succeed)
  - Upload Markdown document (should succeed)
  - Upload TXT document (should succeed)
  - Try uploading 15MB file (should show validation error)
  - Try uploading .docx file (should show validation error)
  - Delete uploaded document (should show confirmation, then remove)

---

### 9.5: Chat Interface - Non-Streaming (Checkpoint 3)

**Key Next.js 16 Patterns:** Client Component for real-time chat interaction, Use React `use` hook for promise streaming (React 19+), Optimistic UI updates before server response.

- [ ] **BFF Route** (`app/api/chat/route.ts`)
  - **POST** `/api/chat` → Proxy to `POST /api/v1/chat` (non-streaming JSON response)
  - Extract JWT from Clerk `auth()`
  - Forward message payload to FastAPI: `{ message: string, stream: false }`
  - Parse `ChatResponse` from backend: content, citations array, quality_score
  - Transform errors for frontend (rate limits, validation errors, server errors)
  - Return JSON response to client

- [ ] **Chat Page** (`app/(dashboard)/chat/page.tsx`)
  - Server Component wrapper for layout
  - Import Client Component for chat UI (message list + input)
  - Responsive design with mobile-first approach

- [ ] **Message Components** (Client Components)
  - **MessageBubble** - Renders individual user/AI messages
    - Props: role, content, citations (optional)
    - User messages: right-aligned, primary color background
    - AI messages: left-aligned, muted background
    - Use shadcn/ui `Avatar` component for user/AI icons
  - **MessageInput** - Chat input with send button
    - shadcn/ui `Textarea` component with auto-resize functionality
    - Send button (shadcn/ui `Button`) or Enter key to submit
    - Shift+Enter for new line
    - Disabled state while message is sending
  - **MessageList** - Scrollable message container
    - shadcn/ui `ScrollArea` component
    - Auto-scroll to bottom on new messages
    - Smooth scroll animation

- [ ] **Chat State Management** (`hooks/useChat.ts`)
  - Custom React hook for managing chat state
  - State: messages array (type: ChatMessage[])
  - State: isLoading boolean (tracks if AI is responding)
  - Function: sendMessage(content: string)
  - Optimistic update: Add user message to state immediately (before API call)
  - Call BFF route: `POST /api/chat`
  - On success: Add AI response to messages array
  - On error: Show error message, allow retry
  - Type-safe with TypeScript interfaces

- [ ] **Message Rendering**
  - User messages: Display message content, timestamp, avatar (right-aligned)
  - AI messages: Display message content, citations, timestamp, avatar (left-aligned)
  - Markdown rendering: Use `react-markdown` package for formatted text
    - Install: `npm install react-markdown`
    - Support: Bold, italic, code blocks, lists, links
  - Citation cards: Below AI messages
    - shadcn/ui `Badge` component for document names
    - Click badge to view source document (future: link to document viewer)
    - Show relevance score (if available)

- [ ] **Citation Display**
  - Render citations below AI message
  - Each citation: document name, snippet preview, relevance score
  - Clickable to navigate to source document (if document viewer implemented)
  - Use shadcn/ui `Card` or `Badge` components for visual consistency

- [ ] **Input Features**
  - Auto-resize textarea as user types (expand vertically)
  - Send on Enter key (preventDefault to avoid new line)
  - Shift+Enter adds new line
  - Character limit indicator (optional, if backend has limit)
  - Disabled state while loading (prevent duplicate sends)
  - Focus on input after message sent (for quick follow-up)

- [ ] **Verify Chat Feature**
  - Send test message: "What is LangGraph?"
  - Verify user message appears immediately (optimistic update)
  - Verify AI response appears after backend responds
  - Verify citations render below AI message
  - Verify Markdown formatting works (bold, code, etc.)
  - Verify auto-scroll to bottom on new messages

---

### 9.6: SSE Streaming & Real-Time Conversational UX

- [ ] **BFF Streaming Route** (`app/api/chat/stream/route.ts`)
  - `POST /api/chat/stream` → `POST /api/v1/chat?stream=true`
  - Forward Clerk JWT
  - Stream SSE events to client (keep connection open)
  - Parse events: `AgentStart`, `Progress`, `Citation`, `Token`, `Validation`, `End`
  - Handle connection errors and reconnection

- [ ] **SSE Client** (`lib/sse-client.ts`)
  - Use native `fetch` with `ReadableStream` (no EventSource needed)
  - Parse SSE event format (`data: {...}\n\n`)
  - Type-safe event handlers
  - AbortController for cancellation

- [ ] **Streaming Message Renderer** (Client Component)
  - Render tokens as they arrive (accumulate in state)
  - Cursor/typing animation at end of message
  - Citations appear after message completes
  - Smooth scroll-to-bottom during streaming

- [ ] **Agent Status Indicator** (Client Component)
  - shadcn/ui `Badge` components for status labels
  - Status transitions: routing → retrieving → generating → validating
  - shadcn/ui `Spinner` for loading state
  - Smooth animations between states

- [ ] **Conversational Features**
  - **Typing Indicator:** Animated dots while waiting for first token
  - **Welcome Message:** Suggest example queries on first load
  - **Follow-up Suggestions:** Display after each response (backend generates)
  - **Message Actions:** Copy message, regenerate response, thumbs up/down

**Key Next.js 15 Patterns:**

- Use React `use` hook to unwrap promises in Client Components
- Stream data progressively with `Suspense` fallbacks
- Keep UI responsive during streaming (no blocking)

---

### 9.7: Rate Limiting & Error Feedback

- [ ] **Rate Limit Handling** (BFF + Client)
  - Detect 429 responses in BFF
  - Parse `X-RateLimit-Remaining`, `X-RateLimit-Reset` headers
  - Forward headers to client

- [ ] **Rate Limit UI** (Client Component)
  - shadcn/ui `Alert` component for rate limit banner
  - Countdown timer until reset
  - Show remaining quota in header (optional)
  - Disable input until reset

- [ ] **Error Handling Strategy**
  - **Network Errors:** Retry with exponential backoff
  - **401 Unauthorized:** Clerk redirects to sign-in automatically
  - **403 Forbidden:** Show permission denied message
  - **429 Rate Limited:** Show banner with countdown
  - **500 Server Error:** Show generic error + retry button
  - **422 Validation Errors:** Show field-specific errors

- [ ] **Error Components**
  - `components/ui/error-boundary.tsx` - React Error Boundary
  - shadcn/ui `Alert` for inline errors
  - shadcn/ui `Sonner` (toast) for transient notifications

**Key Next.js 15 Patterns:**

- Use Server Actions for error logging (future)
- Error boundaries at route level
- Toast notifications for user feedback

---

### 9.8: Responsive Design & shadcn/ui Components

- [ ] **shadcn/ui Component Installation Strategy**
  - Install components as needed (not all at once)
  - Core: `button`, `card`, `input`, `textarea`, `dialog`, `sonner`
  - Layout: `sidebar`, `scroll-area`, `separator`
  - Feedback: `spinner`, `skeleton`, `progress`, `badge`, `alert`
  - Forms: `label`, `checkbox`, `select` (if needed)

- [ ] **Responsive Breakpoints**
  - Mobile-first approach (320px base)
  - Tailwind breakpoints: `sm` (640px), `md` (768px), `lg` (1024px), `xl` (1280px)
  - Collapsible sidebar on mobile (shadcn/ui `Sidebar` component)
  - Touch-friendly buttons (min 44x44px)

- [ ] **Accessibility**
  - ARIA labels on all interactive elements
  - Keyboard navigation (Tab, Enter, Escape)
  - Focus indicators (Tailwind `focus:` variants)
  - Screen reader support (test with VoiceOver)
  - Color contrast (WCAG AA) - built into shadcn/ui themes

- [ ] **Animations**
  - Tailwind transitions and animations
  - Message slide-in/fade-in
  - Loading state transitions
  - Micro-interactions (button hover, etc.)

**shadcn/ui Benefits:**

- Accessible by default (Radix UI primitives)
- Customizable with Tailwind
- Copy-paste components (no npm bloat)
- TypeScript support
- Dark mode ready

---

### 9.9: Server Components & Data Fetching

**Key Next.js 15 Principles:**

- Default to Server Components
- Use Client Components only for interactivity
- Fetch data on the server when possible
- Stream UI with `Suspense` boundaries

- [ ] **Server Component Patterns**
  - Use `async` Server Components for data fetching
  - Call BFF routes directly on server (no client-side fetch)
  - Pass data to Client Components via props
  - Use `Suspense` for loading states

- [ ] **Client Component Patterns**
  - Add `'use client'` directive at top of file
  - Use hooks (`useState`, `useEffect`, `use`)
  - Handle user interactions (onClick, onChange)
  - Keep bundle size small (minimize client JS)

- [ ] **Data Fetching Strategy**
  - Server-side: Direct BFF calls in Server Components
  - Client-side: Fetch from BFF routes via `fetch`
  - Optimistic updates for mutations
  - No global state library needed (use Server Components)

- [ ] **Streaming with `Suspense`**
  - Wrap slow components in `<Suspense fallback={<Skeleton />}>`
  - Use `loading.tsx` for route-level loading states
  - Stream data progressively (Next.js handles automatically)

**Example Flow:**

1. User navigates to `/chat`
2. Server Component fetches conversation history via BFF
3. Client Component renders chat input (interactive)
4. User sends message → Client Component calls BFF `/api/chat/stream`
5. SSE stream updates UI in real-time

---

### 9.10: Testing Strategy

- [ ] **Unit Tests** (Vitest + React Testing Library)
  - Component tests for UI components
  - Hook tests for custom hooks
  - Utility function tests
  - BFF route tests (mock FastAPI responses)

- [ ] **Integration Tests**
  - SSE streaming tests (mock stream events)
  - Authentication flow tests (mock Clerk)
  - Upload flow tests
  - Chat flow tests (non-streaming + streaming)

- [ ] **E2E Tests** (Playwright)
  - Full user flows: sign up → upload → chat
  - Rate limiting behavior
  - Error scenarios
  - Mobile responsiveness

- [ ] **Testing Setup**
  - Install: `vitest`, `@testing-library/react`, `@playwright/test`
  - Install: `msw` (Mock Service Worker) for API mocking
  - Configure: `vitest.config.ts`, `playwright.config.ts`

**Testing Principles:**

- Test behavior, not implementation
- Focus on user interactions
- Mock external dependencies (FastAPI, Clerk)
- Test accessibility (ARIA, keyboard nav)

---

## Backend Changes That MIGHT Be Required

### 🔴 Critical Backend Changes

1. **CORS Configuration** (`backend/app/main.py`)
   - **Issue:** Frontend on different origin (e.g., `http://localhost:3000`) needs CORS enabled
   - **Fix:** Update CORS middleware to allow frontend origin

   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["http://localhost:3000", "https://your-frontend.vercel.app"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

2. **SSE Headers Validation** (`backend/app/api/v1/chat.py`)
   - **Issue:** Ensure SSE responses include proper headers for browser compatibility
   - **Check:** `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `X-Accel-Buffering: no`
   - **Status:** ✅ Likely already implemented, but verify in browser DevTools

### 🟡 Recommended Backend Enhancements

3. **Rate Limit Headers in All Responses** (`backend/app/api/deps.py`)
   - **Why:** Frontend needs to display remaining requests to users
   - **Fix:** Add `X-RateLimit-Remaining`, `X-RateLimit-Limit`, `X-RateLimit-Reset` to all responses
   - **Status:** ✅ Already implemented in Phase 6, verify headers present

4. **Error Response Standardization** (`backend/app/utils/errors.py`)
   - **Why:** Frontend needs consistent error structure for parsing
   - **Check:** All errors return `{ "detail": "message", "code": "ERROR_CODE" }`
   - **Optional:** Add `error_code` field for frontend to handle specific errors

5. **User Feedback Endpoint** (NEW)
   - **Why:** Users can thumbs up/down responses
   - **Endpoint:** `POST /api/v1/feedback`
   - **Payload:** `{ "message_id": "...", "rating": "positive" | "negative", "comment": "..." }`
   - **Priority:** Medium (can be added after MVP)

6. **Conversation History Endpoint** (NEW)
   - **Why:** Store and retrieve past conversations
   - **Endpoints:**
     - `GET /api/v1/conversations` - List user's conversations
     - `GET /api/v1/conversations/{id}` - Get conversation by ID
     - `POST /api/v1/conversations` - Create new conversation
   - **Priority:** Low (can use localStorage initially)

7. **Suggested Queries Endpoint** (NEW)
   - **Why:** Generate contextual follow-up questions
   - **Endpoint:** `POST /api/v1/chat/suggestions`
   - **Payload:** `{ "conversation_id": "...", "last_message": "..." }`
   - **Response:** `{ "suggestions": ["Query 1", "Query 2", "Query 3"] }`
   - **Priority:** Low (nice-to-have for UX)

### 🟢 Optional Backend Improvements

8. **Document Search/Filter** (`backend/app/api/v1/documents.py`)
   - **Why:** Users with many documents need search
   - **Enhancement:** Add query params to `GET /api/v1/documents?q=search&limit=10`
   - **Priority:** Low (defer to post-MVP)

9. **Webhook for Upload Completion** (NEW)
   - **Why:** Notify frontend when async document processing completes
   - **Alternative:** Poll `GET /api/v1/documents/{id}` until `status == "ready"`
   - **Priority:** Low (current sync processing is fast enough)

10. **Health Check for Frontend** (`backend/app/main.py`)
    - **Why:** Frontend can check backend availability
    - **Endpoint:** `GET /health` (already exists) - verify it returns detailed status
    - **Enhancement:** Add `GET /health/ready` for readiness checks

---

## Testing Strategy

### Manual Testing Checklist

- [ ] **Authentication Flow**
  - Sign up with Clerk
  - Sign in and verify session
  - Sign out and verify redirect
  - Protected routes block unauthenticated users

- [ ] **Document Upload**
  - Upload single file (PDF, Markdown, TXT)
  - Upload multiple files
  - Validate file type/size errors
  - View uploaded documents list
  - Delete document with confirmation

- [ ] **Chat (Non-Streaming)**
  - Send message and receive response
  - View citations in response
  - Error handling (network failure, backend error)

- [ ] **Chat (SSE Streaming)**
  - Stream response token by token
  - Agent status updates in real-time
  - Citations appear after streaming completes
  - Cancel stream mid-response

- [ ] **Rate Limiting**
  - Trigger rate limit (send many requests)
  - Verify 429 error message
  - See countdown timer until reset
  - Verify headers in browser DevTools

- [ ] **Error Handling**
  - Network disconnection during upload
  - Invalid JWT token (401)
  - Backend error (500)
  - Validation errors (422)

- [ ] **Responsive Design**
  - Test on mobile (375px width)
  - Test on tablet (768px width)
  - Test on desktop (1440px width)
  - Verify sidebar collapses on mobile

### Automated Testing

- [ ] Unit tests for all hooks
- [ ] Component tests for UI components
- [ ] Integration tests for API client
- [ ] E2E tests for critical flows (sign up → upload → chat)
- [ ] SSE streaming tests with mocked EventSource

---

## Success Criteria for Frontend MVP

✅ **Authentication**

- Users can sign up, sign in, and sign out with Clerk
- Protected routes redirect unauthenticated users
- JWT tokens automatically included in API requests

✅ **Document Management**

- Users can upload documents (PDF, Markdown, TXT)
- Upload shows progress and handles errors
- Users can view and delete their documents

✅ **Chat Interface**

- Users can send messages and receive responses
- SSE streaming shows real-time agent status
- Responses include citations with document references
- Messages render Markdown with syntax highlighting

✅ **Error Handling**

- Network errors show retry options
- Rate limit errors show countdown timer
- Backend errors show user-friendly messages
- All errors logged to console for debugging

✅ **Performance**

- Initial page load < 2 seconds
- Chat response streaming starts < 1 second
- No layout shifts during streaming
- Smooth animations (60fps)

✅ **Accessibility**

- All interactive elements keyboard accessible
- Screen reader support for key features
- WCAG AA color contrast
- ARIA labels on all buttons/inputs

---

## 🎯 NEXT PRIORITIES

### Current Phase: Checkpoint 1 - Project Setup & Authentication ⬅️ START HERE

**Branch:** `frontend`  
**Status:** Ready to begin  
**Prerequisites:** Backend Phase 6 merged to main

**Steps:**

1. Initialize Next.js 15 project
2. Install dependencies (Clerk, Tailwind, etc.)
3. Configure TypeScript (strict mode)
4. Set up Clerk authentication
5. Create base layout and routing
6. Test authentication flow (sign up, sign in, sign out)
7. Create PR #7

**Estimated Time:** 4-6 hours

---

## Future Enhancements (Post-MVP)

- **Dark Mode:** Toggle between light/dark themes
- **Conversation History:** Persist and retrieve past chats
- **Document Search:** Filter uploaded documents
- **Export Conversations:** Download chat as Markdown/PDF
- **Keyboard Shortcuts:** Power user features (Cmd+K command palette)
- **Mobile App:** React Native wrapper for mobile
- **Voice Input:** Speech-to-text for chat input
- **Collaborative Workspaces:** Share documents and chats with team
- **Advanced Citations:** Jump to exact document location from citation

---

## Notes

**Tech Decisions:**

- **Next.js 15 App Router:** Modern React architecture with Server Components
- **Clerk:** Production-ready auth with JWT that matches backend
- **Tailwind CSS:** Utility-first CSS for rapid development
- **Native Fetch:** No external HTTP client needed (fetch + types)
- **SSE over WebSockets:** Simpler for one-way streaming, browser-native

**Deferred Decisions:**

- State management library (start with React Context, add if needed)
- Data fetching library (start with native fetch, add SWR/react-query if needed)
- Component library (build custom with Tailwind, consider shadcn/ui later)

**Assumptions:**

- Backend API is fully functional (Phases 1-6 complete)
- Backend CORS is configured for frontend origin
- Backend returns consistent error responses
- Backend SSE implementation follows standard spec
