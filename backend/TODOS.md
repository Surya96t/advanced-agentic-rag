# Backend Implementation TODO

## Git Branching Strategy

### Checkpoint 1: Core Foundation ✅ COMPLETED

**Branch:** `folder-structure`
**Files:**

- `app/core/config.py` - Settings and environment configuration
- `app/utils/logger.py` - Structured logging with structlog
- `app/utils/errors.py` - Custom exception hierarchy
- `app/schemas/base.py` - Base Pydantic models and common schemas
- `app/database/client.py` - Supabase client singleton
- `app/main.py` - FastAPI app initialization with middleware, error handlers, and health endpoint
- `.env` and `.env.example` - Environment configuration files

**Status:** ✅ App starts successfully, connects to Supabase, health check endpoint works
**PR:** Ready to create

### Checkpoint 2: Document Ingestion ✅ COMPLETED

**Branch:** `feat/document-ingestion`
**Files:** parser, chunkers, embeddings, pipeline, database models/repositories, API endpoint
**Goal:** Can upload and process documents
**Status:** ✅ Full ingestion pipeline implemented and tested
**PR:** Ready to create

### Checkpoint 3: Retrieval System

**Branch:** `feat/retrieval-system`
**Files:** vector search, text search, hybrid search, reranker, query processor
**Goal:** Can search and retrieve relevant chunks

### Checkpoint 4: Agentic RAG (LangGraph)

**Branch:** `feat/agentic-rag`
**Files:** agent nodes, graph, state, tools
**Goal:** Working RAG agent testable via LangGraph Studio and terminal

### Checkpoint 5: API Endpoints

**Branch:** `feat/api-endpoints`
**Files:** health, documents, chat routes (no auth yet)
**Goal:** Full REST API for document upload and queries

### Checkpoint 6: Authentication & Security

**Branch:** `feat/auth-security`
**Files:** auth middleware, user schemas, protected routes
**Goal:** Secure API with JWT authentication

### Checkpoint 7: Testing

**Branch:** `feat/testing`
**Files:** unit tests, integration tests
**Goal:** Comprehensive test coverage

---

## Phase 1: Core Foundation ✅ COMPLETED

- [x] Environment Configuration (`app/core/config.py`)
  - Pydantic Settings for environment variables
  - OpenAI, Supabase, LangSmith configuration
  - Application settings

- [x] Database Setup (`app/database/`)
  - `client.py` - Supabase client initialization with singleton pattern
  - `client.py` - Health check functionality
  - `client.py` - FastAPI dependency injection support
  - Note: Full models will be added in Phase 2

- [x] FastAPI Application (`app/main.py`)
  - App initialization with metadata
  - CORS configuration
  - Middleware setup (logging, error handlers)
  - Global exception handlers for custom errors
  - Router registration (placeholder for future routes)
  - Startup/shutdown events with lifespan manager
  - Health check endpoint

- [x] Base Schemas (`app/schemas/`)
  - `base.py` - Common Pydantic models (BaseSchema, timestamps, pagination, responses)
  - Note: Document and query schemas will be added in later phases

- [x] Utilities (`app/utils/`)
  - `logger.py` - Structured logging with structlog
  - `errors.py` - Custom exception classes hierarchy

---

## Phase 2: Document Ingestion Pipeline ✅ COMPLETED

- [x] Database Models & Repositories (`app/database/`)
  - `models.py` - Document, Source, DocumentChunk Pydantic models with str user_id (Clerk-compatible)
  - `repositories/documents.py` - Document CRUD operations with RLS
  - `repositories/chunks.py` - Chunk batch insertion and retrieval

- [x] Document Processing (`app/ingestion/`)
  - `parser.py` - Markdown/PDF/text parsing with pypdf
  - `chunkers/base.py` - Base chunker interface
  - `chunkers/recursive.py` - RecursiveCharacterTextSplitter with separator detection
  - `chunkers/semantic.py` - Semantic chunking (basic implementation)
  - `chunkers/parent_child.py` - Parent-child chunking strategy
  - `chunkers/contextual.py` - Contextual enrichment chunker
  - `chunkers/code_aware.py` - Code-aware chunking with language detection
  - `embeddings.py` - OpenAI embeddings (text-embedding-3-small, 1536 dims)
  - `pipeline.py` - Full ingestion orchestration with progress tracking, duplicate detection, error handling

- [x] API Endpoint (`app/api/v1/`)
  - `ingest.py` - File upload endpoint with streaming validation, size limits, security hardening

- [x] Integration Tests
  - `tests/test_ingestion_pipeline_integration.py` - Full pipeline tests with real Supabase integration
  - ✅ All tests passing (single document, duplicate detection, multiple documents)

**Status:** ✅ Complete ingestion pipeline ready for production use
**Branch:** `feat/document-ingestion` (pushed to remote)
**Key Features:**

- Clerk-compatible string user IDs throughout
- Robust error handling and metadata tracking
- File upload security (streaming validation, no Content-Length fallback)
- Chunking metadata preservation
- Progress callbacks and duplicate detection

---

## Phase 3: Retrieval System ✅ COMPLETED

**Status:** All core retrieval features implemented and tested  
**Completion Date:** January 2025  
**Documentation:** See `/docs/09_Phase3_Retrieval_Summary.md`

### Completed Features

- [x] Search Components (`app/retrieval/`)
  - `vector_search.py` - Dense vector search (pgvector + OpenAI `text-embedding-3-small`)
  - `text_search.py` - Sparse/full-text search (PostgreSQL FTS with GIN indexing)
  - `hybrid_search.py` - RRF fusion of dense + sparse (k=60, industry standard)
  - `rerankers/flashrank.py` - FlashRank re-ranking (`ms-marco-MiniLM-L-12-v2`)

- [x] Database Schema Optimizations
  - Added `embedding` column (vector(1536)) with pgvector index
  - Added `text_search_vector` column (tsvector) with GIN index
  - Dual indexing strategy for efficient hybrid search

- [x] Code Quality Improvements
  - Eliminated all datetime warnings (introduced `utc_now()` helper)
  - Replaced deprecated `datetime.utcnow()` with timezone-aware alternative
  - Updated all models and schemas for timezone compliance

- [x] Integration Tests (`tests/`)
  - `test_retrieval_integration.py` - 13/13 tests passing
  - Tests use real Supabase, OpenAI, and production documentation (Convex mutations.md)
  - Coverage: vector search, text search, hybrid search, re-ranking

### Features Deferred to Later Phases

**Query Expansion with LLM** → Deferred to Phase 5 (Agentic RAG)

- **Reason:** More valuable in agentic context with multi-step reasoning
- Current hybrid search already delivers strong results without expansion
- Will integrate into LangGraph agent workflows where the agent can decide when to expand queries
- Avoids adding ~500ms latency until proven necessary in agent context

**Cohere Re-ranking** → Deferred to Phase 6 (Optimization)

- **Reason:** FlashRank already meets quality requirements for initial launch
- Avoids API costs (~$0.002 per 1K searches) until validated with production traffic
- Will add as configurable alternative for A/B testing in optimization phase
- Consider hybrid approach: FlashRank for speed, Cohere for quality-critical queries

### Key Metrics

- **Retrieval latency:** ~200-250ms end-to-end (includes OpenAI embedding call)
- **Component breakdown:**
  - Vector search: ~150-200ms (includes OpenAI API)
  - Text search: ~20-30ms (pure PostgreSQL)
  - RRF fusion: ~5ms (in-memory merging)
  - FlashRank re-ranking: ~10-15ms (local model)
- **Test coverage:** 13 integration tests, all passing with real data
- **Quality:** Hybrid search + re-ranking consistently outperforms vector-only or text-only approaches

**Branch:** `feat/retrieval-system` (ready for PR)

---

## Phase 4: Agentic RAG (LangGraph) ✅ COMPLETED

**Status:** ✅ Complete agentic RAG system with LangGraph  
**Completion Date:** January 2025  
**Documentation:** See `/backend/Phase4_todos.md` for detailed checklist

- [x] Agent Nodes (`app/agents/nodes/`)
  - ✅ `router.py` - Query complexity analysis and routing (simple/complex/ambiguous)
  - ✅ `query_expander.py` - Sub-query decomposition and HyDE strategies
  - ✅ `retriever.py` - Multi-query hybrid search with re-ranking
  - ✅ `generator.py` - LLM response synthesis with GPT-4
  - ✅ `validator.py` - Quality checks (attribution, completeness, grounding, retrieval confidence)

- [x] Agent Graph (`app/agents/`)
  - ✅ `graph.py` - Complete LangGraph workflow with state management
  - ✅ `state.py` - AgentState TypedDict with reducers
  - ✅ PostgreSQL checkpointing with `langgraph-checkpoint-postgres`
  - ✅ LangSmith tracing integration
  - ✅ Helper functions: `run_agent()`, `stream_agent()`, `get_checkpoint()`, `resume_agent()`

- [x] Schemas (`app/schemas/`)
  - ✅ `events.py` - SSE event types (AgentStart, Progress, Citation, Token, Validation, End)
  - ✅ `chat.py` - ChatRequest, ChatResponse, FeedbackRequest

- [x] Runtime Validation
  - ✅ LangGraph Studio integration working
  - ✅ End-to-end workflow tested (router → expander → retriever → generator → validator)
  - ✅ Quality score: 0.78 (attribution: 1.00, completeness: 1.00, grounding: 0.77)
  - ✅ All logs and tracing operational

**Branch:** `feat/agentic-rag` (ready for PR)

---

## Phase 5: API Endpoints 🔄 IN PROGRESS

**Current Priority:** Implement REST API endpoints to expose agentic RAG functionality

- [ ] Routes (`app/api/v1/`) ← **START HERE**
  - [x] `health.py` - Health check endpoints (already exists)
  - [x] `ingest.py` - Document upload endpoint (already exists)
  - [ ] `chat.py` - Query endpoint with SSE streaming (no auth) ← **NEXT TASK**
    - [ ] `POST /api/v1/chat` - Non-streaming chat endpoint
    - [ ] `POST /api/v1/chat/stream` - SSE streaming endpoint
    - [ ] Integrate with `stream_agent()` from graph.py
    - [ ] Request validation with ChatRequest schema
    - [ ] Response formatting with ChatResponse schema
    - [ ] Error handling and logging

- [ ] API Dependencies (`app/api/`)
  - [ ] `deps.py` - Shared dependencies (rate limiting, DB sessions)
  - [ ] Rate limiter configuration

- [ ] Router Setup (`app/api/v1/__init__.py`)
  - [ ] Create v1 APIRouter
  - [ ] Include health, ingest, and chat routers
  - [ ] Mount to main app

- [ ] Testing
  - [ ] Test health endpoint
  - [ ] Test chat endpoint with curl/httpie
  - [ ] Test SSE streaming
  - [ ] Test error cases

---

## Phase 6: Authentication & Security

- [ ] Authentication Middleware (`app/core/auth.py`)
  - JWT token validation
  - Supabase Auth integration
  - User context extraction
  - Protected route decorators

- [ ] User Schemas (`app/schemas/`)
  - `user.py` - User schemas

- [ ] Secure API Routes
  - Add auth to document and chat endpoints
  - Admin operations (optional)

---

## Phase 7: Utilities & Observability

- [x] Utilities (`app/utils/`)
  - `logger.py` - ✅ Structured logging with structlog (completed in Phase 1)
  - `errors.py` - ✅ Custom exceptions (completed in Phase 1)
  - `helpers.py` - Common utility functions

- [ ] Observability
  - LangSmith tracing configuration
  - Error tracking
  - Performance monitoring

---

## Phase 8: Testing

- [x] Integration Tests (`tests/`)
  - `test_ingestion_pipeline_integration.py` - Full pipeline integration tests with Supabase
  - ✅ All ingestion tests passing

- [ ] Additional Tests
  - Unit tests for chunkers, parsers, embeddings
  - API endpoint tests (unit + integration)
  - Mocked external services for faster test execution

---

## 🎯 NEXT PRIORITIES

### Recommended Next Steps (in order):

1. **Phase 4: LLM Generation & Response** ⬅️ RECOMMENDED NEXT
   - Implement LLM integration with OpenAI GPT-4
   - Build prompt templates for integration code synthesis
   - Add streaming responses via SSE
   - Context window management and token counting
   - Source attribution in generated responses
   - **Why first:** Core generation logic needed to complete the RAG pipeline (retrieval is done)

2. **Phase 5: API Endpoints (Chat)**
   - Build `/api/v1/chat` endpoint with SSE streaming
   - Integrate retrieval + generation pipeline
   - Add request/response validation
   - Add rate limiting
   - **Why second:** Need generation working to make chat endpoint functional

3. **Phase 6: Agentic RAG (LangGraph)**
   - Build agent nodes (query router, retriever, generator, validator)
   - Create LangGraph workflow with state management
   - Add checkpointing for long-running queries
   - **Integrate query expansion here** (deferred from Phase 3)
   - **Why third:** Build agentic workflows on top of working retrieval + generation

4. **Phase 7: Authentication & Security**
   - Add Clerk JWT validation middleware
   - Protect all endpoints with auth
   - Enforce RLS at API layer
   - **Why fourth:** Productionize the working system

5. **Phase 8: Optimization & Polish**
   - Add LangSmith tracing for observability
   - **Add Cohere re-ranking as configurable option** (deferred from Phase 3)
   - A/B test FlashRank vs Cohere
   - Performance optimization and caching
   - Comprehensive test coverage
   - **Why last:** Optimize and harden the complete system

### Notes on Deferred Features

**From Phase 3:**

- **Query expansion with LLM** will be added in Phase 6 (Agentic RAG) where the agent can intelligently decide when to expand queries
- **Cohere re-ranking** will be added in Phase 8 (Optimization) as a configurable alternative to FlashRank for A/B testing
