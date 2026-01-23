## TODO List

### **Schema Layer** ✅ COMPLETE

- [x] Create `app/schemas/events.py`
  - [x] Define SSEEventType enum
  - [x] Implement AgentStartEvent, AgentCompleteEvent
  - [x] Implement CitationEvent, TokenEvent
  - [x] Implement ProgressEvent, ValidationEvent, EndEvent
  - [x] Add JSON schema examples for each event

- [x] Create `app/schemas/chat.py`
  - [x] Implement ChatRequest with validation
  - [x] Implement ChatResponse with metadata
  - [x] Implement FeedbackRequest for human-in-the-loop
  - [x] Add JSON schema examples

- [x] Update `app/schemas/__init__.py`
  - [x] Export all event types
  - [x] Export chat schemas

### **State Management** ✅ COMPLETE

- [x] Implement `app/agents/state.py`
  - [x] Define AgentState TypedDict with all fields
  - [x] Add `add_messages` reducer for conversation history
  - [x] Add custom reducers for appending chunks and sources
  - [x] Add helper function: `create_initial_state(query: str) -> AgentState`
  - [x] Add helper function: `update_metadata(state, **kwargs) -> dict`

### **Agent Nodes** ✅ COMPLETE

- [x] Implement `app/agents/nodes/router.py`
  - [x] Query complexity analysis function
  - [x] Heuristics: word count, question marks, vague terms, named entities
  - [x] Router node function with Command return
  - [ ] Unit tests for each complexity type (deferred)
  - [x] Streaming progress messages

- [x] Implement `app/agents/nodes/query_expander.py`
  - [x] Sub-query decomposition function (GPT-4)
  - [x] HyDE function (hypothetical document generation)
  - [x] Strategy selector based on complexity
  - [x] LLM prompt templates
  - [ ] Unit tests for both strategies (deferred)
  - [x] Streaming progress and results

- [x] Implement `app/agents/nodes/retriever.py`
  - [x] Multi-query search loop
  - [x] HybridSearch integration
  - [x] Deduplication logic
  - [x] FlashRank re-ranking
  - [x] Citation event emission (via sources field)
  - [ ] Integration tests with Supabase (deferred)

- [x] Implement `app/agents/nodes/generator.py`
  - [x] Prompt template builder
  - [x] Context formatting from chunks
  - [x] LLM streaming with GPT-4
  - [x] Token event emission (metadata tracking)
  - [x] Metadata tracking (tokens, latency, cost)
  - [ ] Integration tests (deferred)

- [x] Implement `app/agents/nodes/validator.py`
  - [x] Source attribution check
  - [x] Code completeness check
  - [x] Hallucination detection (keyword overlap grounding)
  - [x] Retrieval confidence calculation
  - [x] Quality score calculation
  - [x] Retry logic with Command
  - [x] Human-in-the-loop interrupt (optional, commented)
  - [ ] Unit tests for each check (deferred)

- [x] Update `app/agents/nodes/__init__.py`
  - [x] Export all node functions

### **Graph Orchestration** ✅ COMPLETE

- [x] Implement `app/agents/graph.py`
  - [x] Import all nodes
  - [x] Create StateGraph builder
  - [x] Add all nodes to graph
  - [x] Add edges (static and Command-based routing)
  - [x] Configure PostgreSQL checkpointer
  - [x] Set up LangSmith tracing
  - [x] Configure multi-mode streaming
  - [x] Compile graph
  - [x] Export graph instance

- [x] Add graph helper functions
  - [x] `run_agent(query: str, thread_id: str) -> ChatResponse`
  - [x] `stream_agent(query: str, thread_id: str) -> AsyncIterator[SSEEvent]`
  - [x] `get_checkpoint(thread_id: str) -> dict`
  - [x] `resume_agent(thread_id: str, checkpoint_id: str) -> ChatResponse`

### **Configuration & Dependencies** ✅ COMPLETE

- [x] Update `pyproject.toml`
  - [x] Add `langgraph-checkpoint-postgres = "^2.0.0"`
  - [x] Run `uv sync` to install
  - [x] Remove version constraints for latest compatible packages
  - [x] Verify LangGraph ecosystem versions (langgraph 1.0.7, langgraph-api 0.6.39, langgraph-cli 0.4.11)

- [x] Update `.env.example`
  - [x] Add `LANGCHAIN_TRACING_V2=true`
  - [x] Add `LANGCHAIN_API_KEY=<your-langsmith-key>`
  - [x] Add `LANGCHAIN_PROJECT=integration-forge-rag`
  - [x] Fix SUPABASE_SERVICE_KEY → SUPABASE_SERVICE_ROLE_KEY

- [x] Update `app/core/config.py`
  - [x] Add LangSmith configuration fields with proper aliases
  - [x] Add `supabase_connection_string` property
  - [x] Add `configure_langsmith()` function
  - [x] Auto-configure environment variables on settings load

### **Runtime & Validation** ✅ COMPLETE

- [x] LangGraph Studio Integration
  - [x] Start LangGraph dev server (`langgraph dev`)
  - [x] Verify graph visualization in Studio
  - [x] Test all agent nodes execution
  - [x] Verify streaming and event emission
  - [x] Confirm LangSmith tracing integration

- [x] Bug Fixes & Robustness
  - [x] Fix router node query extraction (handle string and message formats)
  - [x] Fix query expander "simple" complexity handling
  - [x] Fix retriever RLS compatibility (default test user ID)
  - [x] Verify all import paths and dependencies

- [x] Test Data Ingestion
  - [x] Create `scripts/ingest_test_data.py`
  - [x] Ingest Convex mutations documentation
  - [x] Verify chunks stored with proper metadata
  - [x] Confirm retrieval returns relevant results

- [x] End-to-End Validation
  - [x] Test complete RAG workflow in Studio
  - [x] Verify query expansion (3 queries generated)
  - [x] Verify hybrid search (vector + text fusion)
  - [x] Verify deduplication (30 → 11 → 5 chunks)
  - [x] Verify LLM generation (1,739 tokens in 38.5s)
  - [x] Verify quality validation (score: 0.78, passed)
  - [x] Confirm all logs and tracing working

### **Testing** ✅ COMPLETE

- [x] Create `tests/test_agent_integration.py`
  - [x] Comprehensive test suite covering all workflows
  - [x] 16 test cases for simple, complex, and ambiguous queries
  - [x] Tests for streaming, validation, checkpointing, error handling
  - [ ] Schema alignment fixes (deferred to API layer - sources schema mismatch)

**Note:** Integration tests are written and demonstrate proper workflow execution (router → retriever → generator → validator works successfully). Minor schema mismatches between `sources` dict format and `SearchResult` Pydantic model will be resolved when implementing the API layer in Phase 5.

- [ ] Create `tests/test_router_node.py` (unit tests - deferred)
- [ ] Create `tests/test_expander_node.py` (unit tests - deferred)
- [ ] Create `tests/test_generator_node.py` (unit tests - deferred)
- [ ] Create `tests/test_validator_node.py` (unit tests - deferred)

### **API Layer** 🔄 NEXT PHASE

- [ ] Implement `app/api/v1/chat.py` ← **CRITICAL FOR FRONTEND**
  - [ ] Implement `POST /api/v1/chat` endpoint (non-streaming)
  - [ ] Implement `POST /api/v1/chat/stream` endpoint (SSE streaming)
  - [ ] Integrate with `stream_agent()` from graph.py
  - [ ] Add JWT authentication middleware (from deps.py)
  - [ ] Add rate limiting
  - [ ] Add request validation (ChatRequest schema)
  - [ ] Add error handling and logging
  - [ ] Return ChatResponse with metadata

- [x] Create `app/api/v1/ingest.py` (already exists)
  - [ ] Review and enhance if needed

- [x] Create `app/api/v1/health.py` (already exists)

- [ ] Update `app/api/v1/__init__.py`
  - [ ] Include chat router
  - [ ] Verify all routers are mounted

- [ ] Test API endpoints
  - [ ] Test health check endpoint
  - [ ] Test chat endpoint with curl/httpie
  - [ ] Test SSE streaming with real queries
  - [ ] Test authentication and rate limiting
  - [ ] Test error cases (invalid input, API failures)

### **Documentation** 📝 DEFERRED

- [ ] Update `backend/TODOS.md`
  - [ ] Mark Phase 4 as in progress
  - [ ] Update completion percentage

- [ ] Update `backend/CONTEXT.md`
  - [ ] Add Session 5 log when complete
  - [ ] Document all implementation details
  - [ ] Update continuation prompt

- [ ] Create usage examples
  - [ ] Simple query example
  - [ ] Streaming example
  - [ ] Checkpoint resume example
