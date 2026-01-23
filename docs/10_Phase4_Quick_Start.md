# Phase 4: Agentic RAG - Quick Start Guide

**Status:** Ready to Begin ✅  
**Full Plan:** See `10_Phase4_Agentic_RAG_Plan.md`

---

## What Was Done (Preparation)

✅ **Research Complete**

- LangGraph v1.0 best practices researched
- State management patterns confirmed (TypedDict + reducers)
- Checkpointing strategy verified (PostgreSQL)
- Streaming modes documented (updates, custom, messages)
- Command pattern for routing confirmed

✅ **Architecture Designed**

- Cyclic reflection loop with retry logic
- 6 agent nodes: Router → Query Expander → Retriever → Generator → Validator
- Quality validation with 2-retry limit
- Human-in-the-loop capability (optional)

✅ **Database & Schemas Reviewed**

- All existing models analyzed
- Response patterns documented
- State schema designed
- SSE event models planned

✅ **Implementation Plan Created**

- 5-phase rollout (5-6 days)
- Detailed TODO checklist (70+ items)
- 11 new files + 5 edits planned
- Success criteria defined

---

## Next: Get Approval & Start

### Option 1: Start Immediately

If you approve the plan as-is, we'll begin **Phase 1** (Schemas & State):

**First Actions:**

1. Create `app/schemas/events.py` (SSE event models)
2. Create `app/schemas/chat.py` (ChatRequest/ChatResponse)
3. Implement `app/agents/state.py` (AgentState TypedDict)
4. Update `app/schemas/__init__.py` (exports)
5. Run tests to verify schema validation

**Estimated Time:** 4-6 hours

### Option 2: Review & Adjust

If you want to:

- Simplify the architecture (skip retry loop?)
- Change streaming approach
- Adjust quality validation criteria
- Remove human-in-the-loop feature

Let me know what to adjust.

### Option 3: Deep Dive First

Want to explore:

- LangGraph Studio setup
- Alternative architectures
- Cost/performance tradeoffs
- Specific implementation details

Ask any questions.

---

## Key Decisions Needed

Before starting, confirm:

1. **LangSmith API Key**: Do you have a LangSmith account for observability?
   - Yes → Add key to `.env`
   - No → We can skip tracing initially

2. **Retry Loop**: Keep 2-retry validation loop?
   - Yes → Improves quality but adds latency
   - No → Single-pass generation (faster)

3. **Human-in-the-Loop**: Implement HITL for borderline responses?
   - Yes → Adds complexity, great for demo
   - No → Skip for now, add later

4. **Streaming**: Use all 3 modes (updates + custom + messages)?
   - Yes → Rich UX, more complex
   - No → Simple updates-only streaming

---

## Quick Command Reference

### Start Development

```bash
# Navigate to backend
cd backend

# Install dependencies (if needed)
uv sync

# Run tests (verify current state)
uv run pytest tests/ -v

# Start dev server (optional, for testing)
uv run uvicorn app.main:app --reload --port 8000
```

### Environment Setup

```bash
# Copy example env (if not already done)
cp .env.example .env

# Add LangSmith keys (optional)
echo "LANGCHAIN_TRACING_V2=true" >> .env
echo "LANGCHAIN_API_KEY=your_key_here" >> .env
echo "LANGCHAIN_PROJECT=integration-forge-rag" >> .env
```

### Install Checkpointer

```bash
# Add to pyproject.toml, then:
uv sync

# Verify installation
uv run python -c "from langgraph.checkpoint.postgres import AsyncPostgresSaver; print('✅ Ready')"
```

---

## Incremental Testing Strategy

After each phase, verify:

**Phase 1 (Schemas):**

```python
# Test schema validation
from app.schemas.events import CitationEvent
event = CitationEvent(chunk_id="...", document_title="...", score=0.85, source="hybrid")
assert event.score == 0.85
```

**Phase 2 (Nodes):**

```python
# Test router node
from app.agents.nodes.router import router_node
result = router_node({"original_query": "How do I install Prisma?"})
assert result["query_complexity"] == "simple"
```

**Phase 3 (Generation):**

```python
# Test generator with mock chunks
result = generator_node({
    "original_query": "...",
    "retrieved_chunks": [...]
})
assert "generated_response" in result
```

**Phase 4 (Graph):**

```python
# Test full graph execution
from app.agents.graph import graph
result = await graph.ainvoke({"original_query": "..."})
assert result["generated_response"]
```

---

## Files You'll Edit (Summary)

### Phase 1: Schemas

- `app/schemas/events.py` (NEW)
- `app/schemas/chat.py` (NEW)
- `app/agents/state.py` (NEW)
- `app/schemas/__init__.py` (EDIT)

### Phase 2: Nodes

- `app/agents/nodes/router.py` (NEW)
- `app/agents/nodes/query_expander.py` (NEW)
- `app/agents/nodes/retriever.py` (NEW)

### Phase 3: Generation

- `app/agents/nodes/generator.py` (NEW)
- `app/agents/nodes/validator.py` (NEW)

### Phase 4: Graph

- `app/agents/graph.py` (EDIT - currently empty)
- `app/core/config.py` (EDIT - add LangSmith)
- `pyproject.toml` (EDIT - add dependency)

### Phase 5: Tests

- `tests/test_agent_integration.py` (NEW)
- `tests/test_router_node.py` (NEW)
- `tests/test_validator_node.py` (NEW)

---

## Ready to Start?

**Just say:**

- "Let's begin Phase 1" → I'll start creating schema files
- "Start Phase 1 now" → Same
- "I approve the plan" → We begin immediately

**Want to adjust?**

- "Skip retry loop" → I'll simplify validator
- "Skip HITL" → I'll remove interrupt logic
- "Simple streaming" → I'll use updates-only mode
- "Show me X first" → I'll explain before implementing

---

**Full Implementation Plan:** `docs/10_Phase4_Agentic_RAG_Plan.md`  
**Your Current Location:** `/Users/surya/Documents/projects/rag-agents/advanced-agentic-rag`
