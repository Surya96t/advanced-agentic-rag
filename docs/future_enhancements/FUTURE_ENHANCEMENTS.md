# Future Enhancements

This document tracks potential improvements and features to implement in future phases of the project.

---

## Response Generation & Quality

### 1. Brevity Detection and Format Constraints
**Priority:** Medium  
**Effort:** Low

**Problem:**
Currently, the generator produces comprehensive, detailed responses regardless of user's format constraints. When users request concise answers (e.g., "in 5 sentences", "briefly"), the system ignores this and generates full tutorials with code examples.

**Options:**

#### Option A: Format Detection in Router (Recommended)
- Router detects format constraints from query
  - Patterns: "in X sentences", "briefly", "one paragraph", "summarize", "TL;DR"
  - Extracts constraint type and parameters
- Pass format metadata to generator via state
- Generator adjusts verbosity based on constraint
  - Brief mode: 3-5 sentences, no code examples
  - Concise mode: 1-2 paragraphs, minimal code
  - Standard mode: Current comprehensive approach (default)

**Benefits:**
- Clean separation of concerns
- Easy to extend with new format types
- Maintains detailed responses as default for integration questions

**Implementation Notes:**
```python
# In router_node
format_constraint = detect_format_constraint(query)
# Examples: {"type": "sentence_count", "value": 5}
#          {"type": "brevity", "value": "brief"}
#          {"type": "standard", "value": None}

# Pass to state
return Command(
    update={
        "query_complexity": complexity,
        "format_constraint": format_constraint,
    },
    goto=next_node
)
```

#### Option B: Brevity Check in Validator
- Validator checks response length against user's constraint
- Fails validation if response is too verbose when brevity requested
- Triggers retry with explicit "be concise" instruction in generator prompt

**Trade-offs:**
- Pro: Catches format violations after generation
- Con: Wastes LLM tokens generating then regenerating
- Con: Adds complexity to validator logic

#### Option C: Separate Generator Prompts
- Maintain multiple generator prompt templates
  - Detailed tutorial prompt (current)
  - Concise factual prompt
  - Brief summary prompt
- Router selects appropriate prompt based on query analysis

**Trade-offs:**
- Pro: Maximum control over output style
- Con: Prompt maintenance overhead
- Con: Doesn't handle nuanced format requests well

**Recommendation:** Implement Option A (Format Detection in Router) when user feedback indicates this is a priority. For an integration-focused RAG system, comprehensive answers are generally preferred.

---

## Performance & Scalability

### 2. Async Supabase Client Migration
**Priority:** High  
**Effort:** Medium

**Problem:**
Current Supabase Python client uses synchronous httpx, causing blocking I/O errors in LangGraph Studio and async environments.

**Current Workaround:**
- Run `langgraph dev --allow-blocking` in development
- Acceptable for development, but not ideal for production deployment

**Solutions:**

#### Option A: Wrap Sync Calls in asyncio.to_thread() (Quick Fix)
```python
# In vector_search.py, hybrid_search.py, text_search.py
import asyncio

async def search(query: str, ...):
    # Wrap the sync Supabase call
    results = await asyncio.to_thread(
        self.client.rpc(...).execute
    )
```

**Benefits:**
- Quick to implement (1-2 hours)
- Minimal code changes
- Works with existing Supabase client

**Trade-offs:**
- Thread overhead for each call
- Not true async (still blocking at thread level)

#### Option B: Migrate to Async Supabase Client (Best Long-term)
Research and implement async Supabase client:
- Check if `supabase-py` has async support
- Evaluate alternative async PostgreSQL clients (asyncpg + PostgREST)
- Refactor all retrieval layer to use async/await throughout

**Benefits:**
- True async, non-blocking I/O
- Better performance under load
- Production-ready for ASGI deployment

**Trade-offs:**
- Larger refactor (4-8 hours)
- May require changing database client library
- Potential breaking changes in retrieval layer

**Recommendation:** Implement Option A (asyncio.to_thread wrapper) in Phase 5 when building API endpoints. Evaluate Option B (full async migration) for Phase 6 (production optimization).

---

## Checkpointing & State Management

### 3. PostgreSQL Checkpointing Integration
**Priority:** Medium  
**Effort:** Medium

**Current State:**
- Lazy import of `AsyncPostgresSaver` implemented
- `get_checkpointer()` helper function created
- Graph compiles without checkpointer at module level
- Checkpointing deferred to runtime

**Remaining Work:**
1. **Add Checkpointer Setup Function**
   ```python
   async def setup_checkpointer():
       """Initialize and set up PostgreSQL checkpointer tables."""
       checkpointer = await get_checkpointer()
       await checkpointer.setup()  # Create required tables
       return checkpointer
   ```

2. **Integrate into API Endpoints (Phase 5)**
   - Initialize checkpointer at FastAPI startup
   - Recompile graph with checkpointer for production routes
   - Keep non-checkpointer version for simple dev/test scenarios

3. **Add Checkpointer Configuration**
   - Add env vars for checkpointer enable/disable
   - Support MemorySaver for dev, PostgreSQL for prod
   - Document connection string requirements

**Implementation Pattern:**
```python
# In FastAPI lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if settings.enable_checkpointing:
        checkpointer = await setup_checkpointer()
        app.state.graph = _builder.compile(checkpointer=checkpointer)
    else:
        app.state.graph = graph  # Use module-level compiled graph
    
    yield
    
    # Shutdown
    if settings.enable_checkpointing:
        await checkpointer.close()
```

**Benefits:**
- Conversation continuity across sessions
- Human-in-the-loop workflows (pause/resume)
- Better debugging with state snapshots
- Production-ready persistence

**Decision Point:** Keep lazy import pattern indefinitely - it's a valid design that prevents module-level import issues while maintaining flexibility for runtime checkpointer initialization.

---

## Agent Intelligence

### 4. Query Complexity Detection Improvements
**Priority:** Low  
**Effort:** Low

**Current Approach:**
- Rule-based detection using keywords and patterns
- Works well for obvious cases

**Potential Improvements:**
- Use LLM to classify query complexity (more accurate but slower/costlier)
- Add complexity scoring (0.0-1.0) instead of just 3 categories
- Learn from user feedback to improve classification

---

## Observability

### 5. Enhanced LangSmith Integration
**Priority:** Low  
**Effort:** Low

**Ideas:**
- Add custom tags per node execution
- Track retry loops and failure patterns
- Monitor validation scores over time
- Dashboard for common query types and success rates

---

## Testing

### 6. Comprehensive Integration Test Suite
**Priority:** High  
**Effort:** Medium

**Current State:**
- Basic integration tests created
- Schema alignment issues identified

**Remaining Work:**
- Fix schema mismatches between agent output and response models
- Add tests for edge cases:
  - Empty retrieval results
  - Network failures
  - Database connection errors
  - Malformed queries
- Add performance benchmarks
- Add streaming tests

---

## Notes

- **Review this document quarterly** to reassess priorities based on user feedback and production needs
- **Mark completed items** with ✅ and move to a CHANGELOG
- **Update effort estimates** as we learn more about implementation complexity
