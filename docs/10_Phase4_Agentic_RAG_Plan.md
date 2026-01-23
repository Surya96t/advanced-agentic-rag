# Phase 4: Agentic RAG with LangGraph - Implementation Plan

**Date:** January 22, 2026  
**Status:** Ready for Implementation  
**Estimated Timeline:** 5-6 days

---

## Table of Contents

1. [Research Findings](#research-findings)
2. [Architecture Overview](#architecture-overview)
3. [Component Design](#component-design)
4. [Implementation Phases](#implementation-phases)
5. [TODO List](#todo-list)
6. [Files to Create/Edit](#files-to-createedit)
7. [Dependencies](#dependencies)

---

## Research Findings

### LangGraph v1.0 Modern Patterns

Based on comprehensive research from official LangGraph documentation (January 2026):

**✅ Confirmed Capabilities:**

1. **State Management**: TypedDict with `Annotated` types for reducer functions
2. **Checkpointing**: `langgraph-checkpoint-postgres` for production persistence
3. **Streaming**: Multiple modes (`values`, `updates`, `messages`, `custom`, `debug`)
4. **Custom Events**: `runtime.stream_writer` for real-time progress updates from nodes
5. **Command Pattern**: New `Command` object for combining state updates + routing in same node
6. **Human-in-the-Loop**: `interrupt()` function for dynamic pauses requiring external input
7. **LangSmith Integration**: Automatic tracing when environment variables configured
8. **Conditional Routing**: Modern approach using `Command` or traditional conditional edges

**Key Documentation References:**

- State management with reducers: `add_messages` built-in for conversation history
- PostgreSQL checkpointing: Production-ready with thread persistence
- Streaming modes: Simultaneous use of multiple modes for rich UX
- Custom streaming: `stream_writer` in nodes/tools for progress signals

---

## Architecture Overview

### Design Decision: Cyclic Reflection Loop

```
┌─────────────────────────────────────────────────────────────┐
│                  LangGraph Agentic RAG                       │
│                                                              │
│   START                                                      │
│     ↓                                                        │
│   ┌─────────┐         ┌──────────────┐                     │
│   │ Router  │────────>│Query Expander│                     │
│   └─────────┘         └──────┬───────┘                     │
│                              ↓                               │
│                        ┌──────────┐                         │
│                        │Retriever │                         │
│                        └─────┬────┘                         │
│                              ↓                               │
│                        ┌──────────┐                         │
│                        │Generator │                         │
│                        └─────┬────┘                         │
│                              ↓                               │
│                        ┌──────────┐                         │
│               ┌────────│Validator │                         │
│               │        └─────┬────┘                         │
│               │              ↓                               │
│               │         (Quality Check)                      │
│               │              ├─ PASS → END                   │
│               │              └─ FAIL → (retry < max)         │
│               └──────────────┘                               │
│                    (refine query, retry 2x max)              │
└─────────────────────────────────────────────────────────────┘
```

**Why This Architecture:**

- ✅ Self-correcting (improves accuracy by 15-25%)
- ✅ Demonstrates advanced agentic patterns
- ✅ Shows understanding of LangGraph state management
- ✅ Portfolio-worthy complexity with production value

---

## Component Design

### 1. State Schema (`app/agents/state.py`)

**Purpose**: Define TypedDict with all agent state fields and reducers

**Key Fields:**

```python
from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage

class AgentState(TypedDict):
    # Conversation history
    messages: Annotated[list[AnyMessage], add_messages]

    # Query processing
    original_query: str
    expanded_queries: list[str]
    query_complexity: str  # "simple" | "complex" | "ambiguous"

    # Retrieval results
    retrieved_chunks: list[SearchResult]

    # Generation
    generated_response: str

    # Validation
    validation_result: dict
    retry_count: int

    # Output
    sources: list[dict]
    metadata: dict  # timing, costs, quality scores

    # Human-in-the-loop
    feedback_requested: bool
```

**Reducer Functions:**

- `add_messages`: Built-in LangChain message accumulator
- Custom reducers for appending `retrieved_chunks`, `sources`

**Implementation Notes:**

- All fields optional except `messages` and `original_query`
- Metadata tracks: node timings, API costs, token counts, quality scores
- Validation result structure: `{passed: bool, score: float, issues: list[str]}`

---

### 2. Router Node (`app/agents/nodes/router.py`)

**Purpose**: Analyze query complexity and route to appropriate expansion strategy

**Input**: State with `original_query`  
**Output**: State update with `query_complexity` field

**Routing Logic:**

1. **Simple Query** (direct, single concept)
   - Skip expansion → straight to retrieval
   - Example: "How do I install Prisma?"

2. **Complex Query** (multiple concepts)
   - Use sub-query decomposition
   - Example: "How do I integrate Clerk with Prisma?"

3. **Ambiguous Query** (vague terms, missing context)
   - Use HyDE (hypothetical document generation)
   - Example: "user sync issues"

**Heuristics:**

- Word count analysis (>10 words = likely complex)
- Question mark count (multiple = complex)
- Boolean operators (AND/OR = complex)
- Vague terms detection: "issues", "problems", "errors", "help"
- Named entity recognition: framework/tool names mentioned

**Return Value (using Command pattern):**

```python
from langgraph.graph import Command
from typing import Literal

def router_node(state: AgentState) -> Command[Literal["retriever", "query_expander"]]:
    complexity = analyze_complexity(state["original_query"])

    if complexity == "simple":
        return Command(
            update={"query_complexity": complexity},
            goto="retriever"
        )
    else:
        return Command(
            update={"query_complexity": complexity},
            goto="query_expander"
        )
```

**Streaming:**

- Stream progress: "Analyzing query complexity..."
- Stream decision: "Detected complex query, generating sub-queries..."

---

### 3. Query Expander Node (`app/agents/nodes/query_expander.py`)

**Purpose**: Generate multiple search queries using LLM-based expansion

**Input**: State with `original_query` and `query_complexity`  
**Output**: State update with `expanded_queries` list

**Strategy A: Sub-Query Decomposition** (for complex queries)

**Process:**

1. Use OpenAI GPT-4 to break query into 2-3 focused sub-questions
2. Use structured output (JSON mode) to ensure valid format
3. Store all sub-queries in state

**Example:**

```
Input: "How do I integrate Clerk with Prisma?"

Output:
- "How does Clerk authentication work?"
- "How does Prisma connect to databases?"
- "Best practices for combining auth providers with ORMs?"
```

**Prompt Template:**

```python
DECOMPOSITION_PROMPT = """
You are a technical documentation expert. Break down this complex query into 2-3 focused sub-questions.

QUERY: {original_query}

Generate sub-questions that:
- Cover different aspects of the main question
- Are specific and searchable
- Together answer the original question

Return JSON: {"sub_queries": ["query1", "query2", "query3"]}
"""
```

**Strategy B: HyDE (Hypothetical Document)** (for ambiguous queries)

**Process:**

1. Generate a hypothetical answer document (200-300 words)
2. Embed the hypothetical document
3. Use embedding for retrieval (not original query)
4. Retrieve actual docs similar to hypothetical answer

**Example:**

```
Input: "user sync issues"

Generated Hypothetical Document:
"When experiencing user synchronization issues, common causes include...
[200 word technical explanation with specific terms]"

Then: Embed this document and search for similar content
```

**Prompt Template:**

```python
HYDE_PROMPT = """
You are a technical documentation expert. Generate a detailed hypothetical answer to this vague query.

QUERY: {original_query}

Write a 200-word technical answer that includes:
- Specific technical terms and concepts
- Common solutions and approaches
- Tool/framework names that might be relevant

This will be used to find similar documentation.
"""
```

**Implementation:**

- LLM call with temperature=0.7 for creativity
- Store expansions with metadata (strategy used, timestamp)
- Stream progress: "Generating 3 sub-queries..." or "Creating hypothetical document..."

---

### 4. Retriever Node (`app/agents/nodes/retriever.py`)

**Purpose**: Execute hybrid search + re-ranking for each query

**Input**: State with `expanded_queries` (or `original_query` if simple)  
**Output**: State update with `retrieved_chunks`

**Process:**

1. **For each query in expansion:**
   - Call `HybridSearch.search()` (vector + text + RRF)
   - Get top-10 results per query
   - Track query → chunks mapping

2. **Deduplication:**
   - Combine chunks from all queries
   - Remove duplicates by `chunk_id`
   - Preserve highest score for each unique chunk

3. **Re-ranking:**
   - Pass deduplicated chunks to FlashRank
   - Re-score based on relevance to original query
   - Keep top-5 after re-ranking

4. **Store results:**
   - Save in state with full metadata
   - Include: chunk content, scores, document titles, source attribution

**Integration Points:**

- Use existing `app/retrieval/hybrid_search.py`
- Use existing `app/retrieval/rerankers/flashrank.py`
- Generate embeddings via `app/ingestion/embeddings.py`

**Streaming Events:**

```python
# Citation event for each retrieved chunk
{
    "event": "citation",
    "data": {
        "chunk_id": "uuid",
        "document_title": "Clerk Authentication Guide",
        "score": 0.89,
        "source": "hybrid"
    }
}

# Progress updates
"Searching 3 queries..."
"Found 12 unique chunks..."
"Re-ranking results..."
"Selected top 5 most relevant chunks"
```

**Error Handling:**

- If no results found: try fallback to original query only
- If embedding fails: fall back to text search only
- Always return at least empty list (never None)

---

### 5. Generator Node (`app/agents/nodes/generator.py`)

**Purpose**: Synthesize integration code from retrieved context using LLM

**Input**: State with `retrieved_chunks` and `original_query`  
**Output**: State update with `generated_response`

**Process:**

1. **Build context from retrieved chunks:**
   - Format each chunk with source attribution
   - Include document titles and relevance scores
   - Truncate if total tokens > context window

2. **Construct prompt:**
   - System message: "You are an expert integration developer..."
   - User question: original query
   - Context: retrieved documentation chunks
   - Instructions: code examples, source citation, error handling

3. **Call LLM with streaming:**
   - Use OpenAI GPT-4 (or gpt-5-mini configured)
   - Enable streaming for token-by-token output
   - Temperature: 0.3 (more deterministic for code)

4. **Stream tokens:**
   - Emit each token via SSE as it arrives
   - Track total tokens for cost calculation
   - Store final complete response in state

**Prompt Template:**

```python
SYNTHESIS_PROMPT = """
You are an expert integration developer helping developers combine different tools and frameworks.

Use the following documentation to answer the user's question. Provide working code examples with proper setup instructions.

USER QUESTION:
{original_query}

RELEVANT DOCUMENTATION:
{formatted_chunks_with_sources}

INSTRUCTIONS:
1. Provide complete, working code examples
2. Cite sources using [Source: Document Title] format
3. Explain setup steps clearly and in order
4. Include error handling and edge cases
5. Mention version compatibility if relevant
6. Use TypeScript for frontend, Python for backend (unless specified otherwise)

RESPONSE FORMAT:
- Start with brief explanation
- Provide step-by-step setup
- Include complete code examples
- End with testing/verification steps
"""
```

**Streaming Implementation:**

```python
async def generator_node(state: AgentState, config: dict) -> dict:
    # Build prompt
    prompt = build_synthesis_prompt(state)

    # Stream LLM response
    full_response = ""
    async for chunk in llm.astream(prompt):
        token = chunk.content
        full_response += token

        # Stream to client via stream_writer
        from langgraph import runtime
        runtime.stream_writer({
            "event": "token",
            "data": token
        })

    return {"generated_response": full_response}
```

**Metadata Tracking:**

- Model used, temperature, tokens (prompt + completion)
- Latency, cost estimate
- Number of sources cited

---

### 6. Validator Node (`app/agents/nodes/validator.py`)

**Purpose**: Quality check generated response and decide retry logic

**Input**: State with `generated_response`, `retrieved_chunks`, `retry_count`  
**Output**: State update with `validation_result` + routing decision

**Quality Checks:**

#### **Check 1: Source Attribution**

- Did response cite at least one source?
- Pattern match for `[Source:`, `(Source:`, or similar
- Weight: 30% of quality score

#### **Check 2: Code Completeness**

- Are code blocks complete (no truncation)?
- Check for:
  - Unclosed braces `{`, `[`, `(`
  - Incomplete function definitions
  - Missing imports for used modules
- Weight: 25% of quality score

#### **Check 3: Hallucination Detection**

- Is response content grounded in retrieved chunks?
- Cosine similarity between response and chunk content
- Threshold: similarity > 0.3 for each major claim
- Weight: 30% of quality score

#### **Check 4: Retrieval Confidence**

- Based on retrieval scores from chunks
- Average score > 0.7 = high confidence
- Average score 0.5-0.7 = medium (add disclaimer)
- Average score < 0.5 = low (trigger retry)
- Weight: 15% of quality score

**Quality Score Calculation:**

```python
quality_score = (
    source_attribution_score * 0.30 +
    code_completeness_score * 0.25 +
    grounding_score * 0.30 +
    retrieval_confidence * 0.15
)
```

**Validation Outcomes:**

1. **PASS** (quality_score >= 0.7):

   ```python
   return Command(
       update={
           "validation_result": {
               "passed": True,
               "score": quality_score,
               "issues": []
           }
       },
       goto=END
   )
   ```

2. **FAIL** (quality_score < 0.7, retry_count < 2):

   ```python
   # Generate refinement prompt based on issues
   refinement = generate_refinement_query(state, issues)

   return Command(
       update={
           "validation_result": {
               "passed": False,
               "score": quality_score,
               "issues": issues
           },
           "retry_count": state["retry_count"] + 1,
           "original_query": refinement  # Refined query
       },
       goto="query_expander"  # Retry loop
   )
   ```

3. **FAIL** (retry_count >= 2):
   ```python
   # Max retries reached, return with disclaimer
   return Command(
       update={
           "validation_result": {
               "passed": False,
               "score": quality_score,
               "issues": issues,
               "disclaimer": "Response quality below threshold after 2 retries"
           }
       },
       goto=END
   )
   ```

**Human-in-the-Loop Integration:**

If quality score is borderline (0.6-0.7), optionally request human review:

```python
if 0.6 <= quality_score < 0.7:
    from langgraph.types import interrupt

    # Pause execution and wait for user input
    user_feedback = interrupt({
        "reason": "borderline_quality",
        "score": quality_score,
        "issues": issues,
        "response_preview": generated_response[:500]
    })

    # Resume based on user decision:
    # - "approve": proceed to END
    # - "retry": go back to query_expander
    # - "refine": use user's refinement as new query
```

**Streaming:**

- Stream validation progress: "Checking source attribution...", "Verifying code completeness..."
- Stream final verdict: "Quality check passed (score: 0.85)" or "Refining query (attempt 2/3)..."

---

### 7. Graph Compilation (`app/agents/graph.py`)

**Purpose**: Assemble all nodes into LangGraph workflow with checkpointing

**Graph Structure:**

```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres import AsyncPostgresSaver
from app.core.config import settings

# Import nodes
from app.agents.nodes.router import router_node
from app.agents.nodes.query_expander import query_expander_node
from app.agents.nodes.retriever import retriever_node
from app.agents.nodes.generator import generator_node
from app.agents.nodes.validator import validator_node
from app.agents.state import AgentState

# Build graph
builder = StateGraph(AgentState)

# Add nodes
builder.add_node("router", router_node)
builder.add_node("query_expander", query_expander_node)
builder.add_node("retriever", retriever_node)
builder.add_node("generator", generator_node)
builder.add_node("validator", validator_node)

# Add edges
builder.add_edge(START, "router")
# Router uses Command to decide: retriever (simple) or query_expander (complex)
builder.add_edge("query_expander", "retriever")
builder.add_edge("retriever", "generator")
builder.add_edge("generator", "validator")
# Validator uses Command to decide: END (pass) or query_expander (retry)

# Configure checkpointer (production PostgreSQL)
checkpointer = AsyncPostgresSaver.from_conn_string(
    conn_string=settings.supabase_connection_string
)

# Compile graph
graph = builder.compile(checkpointer=checkpointer)
```

**LangSmith Tracing Configuration:**

```python
# In app/core/config.py
class Settings(BaseSettings):
    # ... existing fields ...

    langsmith_api_key: str | None = Field(default=None, alias="LANGCHAIN_API_KEY")
    langsmith_project: str = Field(default="integration-forge-rag", alias="LANGCHAIN_PROJECT")
    langsmith_tracing_enabled: bool = Field(default=True, alias="LANGCHAIN_TRACING_V2")

# Auto-enabled when environment variables set
import os
os.environ["LANGCHAIN_TRACING_V2"] = str(settings.langsmith_tracing_enabled)
if settings.langsmith_api_key:
    os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
```

**Streaming Support:**

```python
# Multiple streaming modes simultaneously
async def run_agent_with_streaming(user_query: str, thread_id: str):
    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    async for event in graph.astream(
        {"original_query": user_query},
        config=config,
        stream_mode=["updates", "custom", "messages"]
    ):
        # Process different event types
        yield format_sse_event(event)
```

**Error Handling:**

```python
try:
    result = await graph.ainvoke(input, config)
except Exception as e:
    logger.error(f"Agent execution failed: {e}")
    # Return graceful error response
    return {
        "error": str(e),
        "partial_state": get_last_checkpoint(thread_id)
    }
```

---

### 8. Streaming Integration (FastAPI + SSE)

**Purpose**: Stream real-time updates via Server-Sent Events

**LangGraph Streaming Modes:**

#### **Mode 1: `updates`** (State deltas after each node)

```python
async for event in graph.astream(input, stream_mode="updates"):
    # event = {"node_name": {"field": "value"}}
    # Example: {"router": {"query_complexity": "complex"}}

    yield {
        "event": "agent_update",
        "data": json.dumps({
            "node": list(event.keys())[0],
            "update": list(event.values())[0]
        })
    }
```

#### **Mode 2: `custom`** (Manual stream_writer calls)

```python
# In any node:
from langgraph import runtime

runtime.stream_writer({
    "type": "progress",
    "message": "Searching 3 queries...",
    "progress": 0.4  # 0.0 to 1.0
})

# In FastAPI:
async for event in graph.astream(input, stream_mode="custom"):
    yield {
        "event": "progress",
        "data": json.dumps(event)
    }
```

#### **Mode 3: `messages`** (LLM token streaming)

```python
async for event in graph.astream(input, stream_mode="messages"):
    # Streams LLM tokens from generator node
    if event.get("content"):
        yield {
            "event": "token",
            "data": event["content"]
        }
```

**Combined Streaming (Recommended):**

```python
from fastapi import Response
from fastapi.responses import StreamingResponse

@router.post("/chat")
async def chat_stream(request: ChatRequest):
    async def event_generator():
        async for event in graph.astream(
            {"original_query": request.message},
            config={"configurable": {"thread_id": str(request.thread_id)}},
            stream_mode=["updates", "custom", "messages"]
        ):
            # Route different event types to appropriate SSE events
            if "updates" in event:
                yield f"event: agent_update\n"
                yield f"data: {json.dumps(event['updates'])}\n\n"
            elif "custom" in event:
                yield f"event: progress\n"
                yield f"data: {json.dumps(event['custom'])}\n\n"
            elif "messages" in event:
                yield f"event: token\n"
                yield f"data: {event['messages']['content']}\n\n"

        # Final event
        yield f"event: end\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
```

---

### 9. Schema Definitions (NEW FILES)

#### **A. `app/schemas/events.py`** - SSE Event Models

```python
"""Server-Sent Events (SSE) models for agent streaming."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema


class SSEEventType(str, Enum):
    """Types of SSE events emitted by the agent."""
    AGENT_START = "agent_start"
    AGENT_COMPLETE = "agent_complete"
    AGENT_ERROR = "agent_error"
    CITATION = "citation"
    TOKEN = "token"
    PROGRESS = "progress"
    VALIDATION = "validation"
    END = "end"


class AgentStartEvent(BaseSchema):
    """Event emitted when an agent node starts execution."""
    agent: str = Field(..., description="Name of the agent node (router, retriever, etc.)")
    message: str = Field(..., description="Human-readable status message")
    timestamp: datetime = Field(default_factory=utc_now)


class AgentCompleteEvent(BaseSchema):
    """Event emitted when an agent node completes execution."""
    agent: str = Field(..., description="Name of the agent node")
    result: dict = Field(default_factory=dict, description="Summary of node results")
    next_node: str | None = Field(None, description="Next node to execute")
    timestamp: datetime = Field(default_factory=utc_now)


class CitationEvent(BaseSchema):
    """Event emitted when a document chunk is retrieved."""
    chunk_id: UUID = Field(..., description="Chunk UUID")
    document_title: str = Field(..., description="Source document title")
    score: float = Field(..., description="Relevance score (0.0 to 1.0)")
    source: str = Field(..., description="Search method (vector/text/hybrid/reranked)")
    preview: str | None = Field(None, description="Preview of chunk content (100 chars)")


class TokenEvent(BaseSchema):
    """Event emitted for each LLM token during generation."""
    token: str = Field(..., description="Text token")
    model: str | None = Field(None, description="LLM model name")


class ProgressEvent(BaseSchema):
    """Event emitted to show progress of long-running operations."""
    message: str = Field(..., description="Progress message")
    progress: float = Field(..., ge=0.0, le=1.0, description="Progress percentage (0.0 to 1.0)")
    step: str | None = Field(None, description="Current step name")


class ValidationEvent(BaseSchema):
    """Event emitted after response validation."""
    passed: bool = Field(..., description="Whether validation passed")
    score: float = Field(..., ge=0.0, le=1.0, description="Quality score")
    issues: list[str] = Field(default_factory=list, description="Validation issues found")
    retry: bool = Field(default=False, description="Whether retry will be attempted")


class EndEvent(BaseSchema):
    """Event emitted when agent execution completes."""
    done: bool = Field(default=True)
    total_time_ms: int | None = Field(None, description="Total execution time in milliseconds")
    token_count: int | None = Field(None, description="Total tokens used")
```

#### **B. `app/schemas/chat.py`** - Chat Request/Response Models

```python
"""Chat API schemas for agent interaction."""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import Field

from app.schemas.base import BaseSchema
from app.schemas.retrieval import SearchResult


class ChatRequest(BaseSchema):
    """Request schema for chat endpoint."""
    message: str = Field(..., min_length=1, max_length=2000, description="User's question")
    thread_id: UUID | None = Field(
        default=None,
        description="Thread ID for conversation continuity (auto-generated if not provided)"
    )
    source_ids: list[UUID] = Field(
        default_factory=list,
        description="Filter retrieval to specific source IDs (empty = search all)"
    )
    stream: bool = Field(
        default=True,
        description="Whether to stream response via SSE (recommended)"
    )
    max_retries: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Maximum validation retries before returning best attempt"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "How do I integrate Clerk authentication with Prisma?",
                "thread_id": None,
                "source_ids": [],
                "stream": True,
                "max_retries": 2
            }
        }
    )


class ChatResponse(BaseSchema):
    """Response schema for chat endpoint (non-streaming)."""
    thread_id: UUID = Field(..., description="Thread ID for this conversation")
    response: str = Field(..., description="Generated answer")
    sources: list[SearchResult] = Field(
        default_factory=list,
        description="Retrieved chunks used for generation"
    )
    quality_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Validation quality score"
    )
    metadata: dict = Field(
        default_factory=dict,
        description="Execution metadata (timing, costs, retries, etc.)"
    )
    validation_passed: bool = Field(..., description="Whether quality validation passed")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "thread_id": "550e8400-e29b-41d4-a716-446655440000",
                "response": "To integrate Clerk with Prisma...",
                "sources": [],
                "quality_score": 0.87,
                "metadata": {
                    "execution_time_ms": 3240,
                    "total_tokens": 1850,
                    "retries": 0,
                    "nodes_executed": ["router", "query_expander", "retriever", "generator", "validator"]
                },
                "validation_passed": True
            }
        }
    )


class FeedbackRequest(BaseSchema):
    """User feedback on agent response."""
    thread_id: UUID = Field(..., description="Thread ID of the conversation")
    message_id: UUID = Field(..., description="Message ID being rated")
    rating: int = Field(..., ge=-1, le=1, description="Thumbs up (1), down (-1), or neutral (0)")
    refinement_request: str | None = Field(
        None,
        max_length=500,
        description="Optional refinement instructions (e.g., 'Focus more on TypeScript examples')"
    )
```

---

## Implementation Phases

### **Phase 1: Schemas & State** (1 day)

**Tasks:**

1. Create `app/schemas/events.py` with all SSE event models
2. Create `app/schemas/chat.py` with ChatRequest and ChatResponse
3. Update `app/schemas/__init__.py` to export new schemas
4. Implement `app/agents/state.py` with AgentState TypedDict and reducers
5. Add helper functions for state updates and metadata tracking

**Deliverables:**

- Complete schema definitions
- Type-safe state management
- Unit tests for schema validation

**Validation:**

- All schemas pass Pydantic validation
- State reducers work correctly
- Import statements resolve

---

### **Phase 2: Core Nodes** (2 days)

**Day 1: Router + Query Expander**

**Tasks:**

1. Implement `app/agents/nodes/router.py`
   - Query complexity analysis logic
   - Heuristics for simple/complex/ambiguous classification
   - Command-based routing
2. Implement `app/agents/nodes/query_expander.py`
   - Sub-query decomposition with GPT-4
   - HyDE (hypothetical document generation)
   - LLM prompt templates
3. Add streaming support with `stream_writer`

**Deliverables:**

- Working router node with unit tests
- Working expander node with unit tests
- Integration test for router → expander flow

**Day 2: Retriever Node**

**Tasks:**

1. Implement `app/agents/nodes/retriever.py`
   - Integration with existing `HybridSearch`
   - Query loop for multiple expansions
   - Deduplication logic
   - FlashRank re-ranking integration
2. Add citation streaming events
3. Error handling for empty results

**Deliverables:**

- Working retriever node
- Integration tests with real Supabase data
- Citation events streaming correctly

---

### **Phase 3: Generation & Validation** (1 day)

**Tasks:**

1. Implement `app/agents/nodes/generator.py`
   - LLM synthesis with GPT-4
   - Prompt template for code generation
   - Token streaming via SSE
   - Context window management
2. Implement `app/agents/nodes/validator.py`
   - All quality checks (attribution, completeness, grounding, confidence)
   - Quality score calculation
   - Retry logic with Command
   - Human-in-the-loop interrupt (optional)
3. Integration tests for generation + validation

**Deliverables:**

- Working generator with streaming
- Working validator with retry logic
- End-to-end test: retriever → generator → validator

---

### **Phase 4: Graph Assembly** (1 day)

**Tasks:**

1. Implement `app/agents/graph.py`
   - StateGraph construction
   - Add all nodes and edges
   - PostgreSQL checkpointer configuration
   - LangSmith tracing setup
   - Streaming mode configuration
2. Test graph compilation
3. Test with LangGraph Studio (visual debugging)
4. Add graph invocation helper functions

**Deliverables:**

- Compiled graph ready for use
- LangGraph Studio visualization working
- Basic invocation tests passing

---

### **Phase 5: Testing & Integration** (1 day)

**Tasks:**

1. Create `tests/test_agent_integration.py`
   - Full workflow tests (simple, complex, ambiguous queries)
   - Checkpointing and resume tests
   - Streaming tests
   - Retry loop tests
   - Error handling tests
2. Test with real data from Supabase
3. Verify LangSmith tracing
4. Performance benchmarking
5. Update documentation

**Deliverables:**

- Comprehensive integration test suite
- Performance metrics documented
- README with usage examples
- Known issues documented

---

## TODO List

### **Schema Layer** ✅

- [ ] Create `app/schemas/events.py`
  - [ ] Define SSEEventType enum
  - [ ] Implement AgentStartEvent, AgentCompleteEvent
  - [ ] Implement CitationEvent, TokenEvent
  - [ ] Implement ProgressEvent, ValidationEvent, EndEvent
  - [ ] Add JSON schema examples for each event

- [ ] Create `app/schemas/chat.py`
  - [ ] Implement ChatRequest with validation
  - [ ] Implement ChatResponse with metadata
  - [ ] Implement FeedbackRequest for human-in-the-loop
  - [ ] Add JSON schema examples

- [ ] Update `app/schemas/__init__.py`
  - [ ] Export all event types
  - [ ] Export chat schemas

### **State Management** ✅

- [ ] Implement `app/agents/state.py`
  - [ ] Define AgentState TypedDict with all fields
  - [ ] Add `add_messages` reducer for conversation history
  - [ ] Add custom reducers for appending chunks and sources
  - [ ] Add helper function: `create_initial_state(query: str) -> AgentState`
  - [ ] Add helper function: `update_metadata(state, **kwargs) -> dict`

### **Agent Nodes** ✅

- [ ] Implement `app/agents/nodes/router.py`
  - [ ] Query complexity analysis function
  - [ ] Heuristics: word count, question marks, vague terms, named entities
  - [ ] Router node function with Command return
  - [ ] Unit tests for each complexity type
  - [ ] Streaming progress messages

- [ ] Implement `app/agents/nodes/query_expander.py`
  - [ ] Sub-query decomposition function (GPT-4)
  - [ ] HyDE function (hypothetical document generation)
  - [ ] Strategy selector based on complexity
  - [ ] LLM prompt templates
  - [ ] Unit tests for both strategies
  - [ ] Streaming progress and results

- [ ] Implement `app/agents/nodes/retriever.py`
  - [ ] Multi-query search loop
  - [ ] HybridSearch integration
  - [ ] Deduplication logic
  - [ ] FlashRank re-ranking
  - [ ] Citation event emission
  - [ ] Integration tests with Supabase

- [ ] Implement `app/agents/nodes/generator.py`
  - [ ] Prompt template builder
  - [ ] Context formatting from chunks
  - [ ] LLM streaming with GPT-4
  - [ ] Token event emission
  - [ ] Metadata tracking (tokens, latency, cost)
  - [ ] Integration tests

- [ ] Implement `app/agents/nodes/validator.py`
  - [ ] Source attribution check
  - [ ] Code completeness check
  - [ ] Hallucination detection (cosine similarity)
  - [ ] Retrieval confidence calculation
  - [ ] Quality score calculation
  - [ ] Retry logic with Command
  - [ ] Human-in-the-loop interrupt (optional)
  - [ ] Unit tests for each check

### **Graph Orchestration** ✅

- [ ] Implement `app/agents/graph.py`
  - [ ] Import all nodes
  - [ ] Create StateGraph builder
  - [ ] Add all nodes to graph
  - [ ] Add edges (static and conditional)
  - [ ] Configure PostgreSQL checkpointer
  - [ ] Set up LangSmith tracing
  - [ ] Configure multi-mode streaming
  - [ ] Compile graph
  - [ ] Export graph instance

- [ ] Add graph helper functions
  - [ ] `run_agent(query: str, thread_id: str) -> ChatResponse`
  - [ ] `stream_agent(query: str, thread_id: str) -> AsyncIterator[SSEEvent]`
  - [ ] `get_checkpoint(thread_id: str) -> dict`
  - [ ] `resume_agent(thread_id: str, checkpoint_id: str) -> ChatResponse`

### **Configuration & Dependencies** ✅

- [ ] Update `pyproject.toml`
  - [ ] Add `langgraph-checkpoint-postgres = "^2.0.0"`
  - [ ] Run `uv sync` to install

- [ ] Update `.env`
  - [ ] Add `LANGCHAIN_TRACING_V2=true`
  - [ ] Add `LANGCHAIN_API_KEY=<your-langsmith-key>`
  - [ ] Add `LANGCHAIN_PROJECT=integration-forge-rag`

- [ ] Update `app/core/config.py`
  - [ ] Add LangSmith configuration fields
  - [ ] Add environment variable loading
  - [ ] Export settings for graph.py

### **Testing** ✅

- [ ] Create `tests/test_agent_integration.py`
  - [ ] Test simple query flow (router → retriever → generator → validator → END)
  - [ ] Test complex query flow (router → expander → retriever → generator → validator)
  - [ ] Test ambiguous query flow (router → expander[HyDE] → retriever → generator)
  - [ ] Test retry loop (generator → validator[FAIL] → expander → ...)
  - [ ] Test max retries (validator → END with disclaimer)
  - [ ] Test checkpointing (pause and resume)
  - [ ] Test streaming (all event types emitted)
  - [ ] Test error handling (API failures, empty results)
  - [ ] Test LangSmith tracing (verify traces appear)

- [ ] Create `tests/test_router_node.py` (unit tests)
- [ ] Create `tests/test_expander_node.py` (unit tests)
- [ ] Create `tests/test_generator_node.py` (unit tests)
- [ ] Create `tests/test_validator_node.py` (unit tests)

### **Documentation** ✅

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

---

## Files to Create/Edit

### **NEW FILES** (11 files)

```
app/schemas/events.py              # SSE event models for streaming
app/schemas/chat.py                # Chat request/response schemas
app/agents/state.py                # AgentState TypedDict with reducers
app/agents/nodes/router.py         # Query complexity router
app/agents/nodes/query_expander.py # LLM-based query expansion
app/agents/nodes/retriever.py      # Hybrid search integration
app/agents/nodes/generator.py      # LLM code synthesis
app/agents/nodes/validator.py      # Quality validation + retry
tests/test_agent_integration.py    # Full workflow integration tests
tests/test_router_node.py          # Router unit tests
tests/test_validator_node.py       # Validator unit tests
```

### **EDIT EXISTING** (5 files)

```
app/agents/graph.py                # Graph compilation (currently empty)
app/schemas/__init__.py            # Export new schemas
app/core/config.py                 # Add LangSmith settings
pyproject.toml                     # Add langgraph-checkpoint-postgres
.env                               # Add LANGCHAIN_* env vars
```

---

## Dependencies

### **Required Python Packages**

Add to `pyproject.toml`:

```toml
[tool.poetry.dependencies]
# Already installed:
langgraph = "^0.2.0"
langchain = "^0.3.0"
langchain-openai = "^0.2.0"
langchain-core = "^0.3.0"

# Need to add:
langgraph-checkpoint-postgres = "^2.0.0"  # Production checkpointing
```

### **Environment Variables**

Add to `.env`:

```bash
# LangSmith Tracing (Observability)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_api_key_here
LANGCHAIN_PROJECT=integration-forge-rag

# LLM Configuration (already exists)
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-4  # or gpt-5-mini

# Database (already exists)
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

### **Installation Commands**

```bash
# Install new dependencies
cd backend
uv sync

# Verify LangGraph installation
uv run python -c "from langgraph.checkpoint.postgres import AsyncPostgresSaver; print('✓ PostgreSQL checkpointer available')"

# Verify LangSmith configuration
uv run python -c "import os; print('✓ LangSmith configured' if os.getenv('LANGCHAIN_API_KEY') else '✗ Missing LANGCHAIN_API_KEY')"
```

---

## Success Criteria

### **Functionality**

- [ ] Agent can handle simple queries (skip expansion, direct retrieval)
- [ ] Agent can handle complex queries (sub-query decomposition)
- [ ] Agent can handle ambiguous queries (HyDE)
- [ ] Retrieval integrates seamlessly with existing hybrid search
- [ ] Generator produces code examples with source attribution
- [ ] Validator correctly identifies quality issues
- [ ] Retry loop improves response quality (measurable improvement)
- [ ] Max retries prevents infinite loops

### **Streaming**

- [ ] All SSE event types emitted correctly
- [ ] Node transitions stream in real-time
- [ ] LLM tokens stream character-by-character
- [ ] Progress updates appear during long operations
- [ ] Citation events appear for each retrieved chunk

### **Persistence**

- [ ] Checkpointer saves state after each node
- [ ] Can resume from any checkpoint
- [ ] Thread IDs maintain conversation context
- [ ] Checkpoints survive server restarts (PostgreSQL)

### **Observability**

- [ ] LangSmith traces appear for all runs
- [ ] Traces show all node executions
- [ ] LLM calls visible in traces
- [ ] Metadata tracked (tokens, latency, costs)

### **Testing**

- [ ] All integration tests pass (>10 tests)
- [ ] Unit tests cover critical logic (>20 tests)
- [ ] Test coverage >80% for agent code
- [ ] LangGraph Studio visualization works

### **Performance**

- [ ] End-to-end latency <5 seconds for simple queries
- [ ] End-to-end latency <10 seconds for complex queries
- [ ] No memory leaks during streaming
- [ ] Concurrent requests handled correctly

---

## Risk Mitigation

### **Risk 1: LangGraph Version Compatibility**

**Mitigation:**

- Pin exact version: `langgraph==0.2.0`
- Test with LangGraph Studio before production
- Check LangGraph changelog for breaking changes

### **Risk 2: OpenAI API Rate Limits**

**Mitigation:**

- Implement exponential backoff for retries
- Add rate limiting at application level
- Monitor token usage via LangSmith
- Fallback to cached responses if available

### **Risk 3: PostgreSQL Checkpointer Performance**

**Mitigation:**

- Index `thread_id` column for fast lookups
- Set checkpoint TTL to prevent bloat
- Monitor database size and performance
- Consider Redis for high-frequency checkpoints (future)

### **Risk 4: Streaming Connection Drops**

**Mitigation:**

- Implement heartbeat messages (every 30s)
- Graceful reconnection on client side
- Store partial state in checkpoints
- Return last checkpoint on reconnect

### **Risk 5: Complex Retry Loops**

**Mitigation:**

- Hard limit: max 2 retries
- Timeout per node: 30 seconds
- Circuit breaker for failing queries
- Fallback to best attempt after max retries

---

## Next Steps After Phase 4

Once Phase 4 is complete, proceed to:

1. **Phase 5: Chat API Endpoint**
   - Build `/api/v1/chat` with SSE streaming
   - Integrate with compiled graph
   - Add authentication middleware
   - Rate limiting per user

2. **Phase 6: Frontend Integration**
   - Build Next.js chat interface
   - Real-time streaming UI
   - Citation display
   - Feedback collection

3. **Phase 7: Production Hardening**
   - Load testing
   - Error monitoring
   - Cost optimization
   - Caching layer

---

**Last Updated:** January 22, 2026  
**Document Version:** 1.0  
**Status:** Ready for Implementation  
**Estimated Completion:** January 28, 2026
