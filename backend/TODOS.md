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

### Checkpoint 2: Document Ingestion

**Branch:** `feat/document-ingestion`
**Files:** parser, chunker, embedder, pipeline, vectorstore, document schemas
**Goal:** Can upload and process documents

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

## Phase 2: Document Ingestion Pipeline

- [ ] Document Processing (`app/ingestion/`)
  - `parser.py` - PDF/text parsing with pypdf
  - `chunker.py` - Multi-stage chunking (RecursiveCharacter, Semantic, etc.)
  - `embedder.py` - OpenAI embeddings generation
  - `pipeline.py` - Orchestration of parsing → chunking → embedding

- [ ] Vector Storage (`app/ingestion/`)
  - `vectorstore.py` - Supabase pgvector operations
  - Batch insertion with metadata
  - Document indexing

---

## Phase 3: Retrieval System

- [ ] Search Components (`app/retrieval/`)
  - `vector_search.py` - Dense vector search
  - `text_search.py` - Sparse/full-text search
  - `hybrid_search.py` - RRF fusion of dense + sparse
  - `reranker.py` - FlashRank + Cohere re-ranking

- [ ] Query Processing (`app/retrieval/`)
  - `query_processor.py` - Query expansion with LLM
  - `context_builder.py` - Assembling context from chunks

---

## Phase 4: Agentic RAG (LangGraph)

- [ ] Agent Nodes (`app/agents/nodes/`)
  - `query_analyzer.py` - Analyze and route queries
  - `retriever.py` - Call retrieval system
  - `synthesizer.py` - Generate final response
  - `validator.py` - Validate and refine responses

- [ ] Agent Graph (`app/agents/`)
  - `graph.py` - LangGraph workflow definition
  - `state.py` - Graph state schema
  - `checkpointing.py` - Checkpoint configuration

- [ ] Agent Tools (`app/agents/tools/`)
  - Custom tools for the agent (if needed)

---

## Phase 5: API Endpoints

- [ ] Routes (`app/api/routes/`)
  - `health.py` - Health check endpoints
  - `documents.py` - Upload, list, delete documents (no auth)
  - `chat.py` - Query endpoint with SSE streaming (no auth)

- [ ] API Dependencies (`app/api/`)
  - `dependencies.py` - Shared dependencies (DB, rate limiting)

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

- [ ] Tests (`tests/`)
  - Unit tests for each module
  - Integration tests for API endpoints
  - Mocked external services
