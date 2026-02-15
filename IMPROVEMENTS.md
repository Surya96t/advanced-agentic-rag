# Integration Forge - Recommended Improvements

**Document Created:** February 14, 2026  
**Last Updated:** February 14, 2026  
**Status:** Pending Implementation

---

## Executive Summary

This document outlines recommended improvements for the Integration Forge RAG system based on the latest LangChain/LangGraph v1 documentation (February 2026) and modern Next.js 15+ best practices.

### Key Updates
- **LangGraph v1** released January 2026 with stable APIs
- **LangChain v1** emphasis on auto-streaming and `messages` mode
- **Command Pattern** is the modern replacement for conditional edges
- **PostgreSQL Checkpointing** confirmed as production-ready pattern

---

## 🔧 Backend Improvements

### Priority 1: Modernize LLM Token Streaming (HIGH IMPACT)

**Current Implementation:**
- Manual token emission using `get_stream_writer()` in generator node
- Custom events with `{"type": "token", "token": "..."}` format
- Stream mode: `["updates", "custom"]`

**Recommended Approach:**
```python
# backend/app/agents/nodes/generator.py
async def generator_node(state: AgentState) -> dict:
    """
    Generator node (simplified with auto-streaming).
    
    No manual writer() calls needed - LangChain auto-streams
    when parent graph is in streaming mode!
    """
    query = state["original_query"]
    chunks = state.get("retrieved_chunks", [])
    
    context = format_context(chunks)
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=USER_PROMPT_TEMPLATE.format(
            query=query, context=context
        ))
    ]
    
    # Just use ainvoke() - auto-streams if graph is streaming!
    # LangChain detects streaming context and delegates internally
    response = await llm.ainvoke(messages)
    
    # Token counting and state update
    prompt_tokens = count_chat_tokens(messages, model=settings.openai_model)
    completion_tokens = count_tokens(response.content, model=settings.openai_model)
    
    return {
        "messages": [AIMessage(content=response.content)],
        "generated_response": response.content,
        "metadata": {
            "generation": {
                "model": settings.openai_model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            }
        }
    }
```

**Updated Graph Streaming:**
```python
# backend/app/agents/graph.py

async def stream_agent(...) -> AsyncIterator[dict]:
    """Stream with 'messages' mode for automatic LLM token streaming."""
    
    # Use "messages" instead of "custom" for token streaming
    async for chunk in graph_instance.astream(
        initial_state,
        config=config,
        stream_mode=["updates", "messages"],  # ← Changed from "custom"
    ):
        mode, data = chunk
        
        if mode == "updates":
            # Handle state updates (citations, agents, etc.)
            # ... existing logic ...
            
        elif mode == "messages":
            # Auto-captured LLM tokens (tuple format)
            message_chunk, metadata = data
            
            if message_chunk.content:
                yield {
                    "event": SSEEventType.TOKEN.value,
                    "data": TokenEvent(
                        token=message_chunk.content,
                        model=metadata.get("langgraph_node"),  # Node name
                    ).model_dump_json()
                }
```

**Benefits:**
- ✅ **Less code** - Remove ~30 lines of manual writer logic
- ✅ **Better metadata** - Includes node name, tags, run IDs automatically
- ✅ **Works everywhere** - Tokens from ANY LLM call (nodes, tools, subgraphs)
- ✅ **Future-proof** - Aligned with LangChain v1 patterns
- ✅ **Performance** - LangChain's optimized streaming under the hood

**Files to Update:**
1. `backend/app/agents/nodes/generator.py` - Simplify to use `ainvoke()`
2. `backend/app/agents/graph.py` - Change `stream_mode=["updates", "messages"]`
3. `backend/app/api/v1/chat.py` - Handle `"messages"` events instead of `"custom"`

**Migration Risk:** 🟡 Medium
- Frontend SSE parsing needs minor update
- Fully backward compatible with `TokenEvent` schema

---

### Priority 2: Enhanced Error Handling & Observability

**Current State:**
- Basic error logging
- No structured tracing beyond LangSmith

**Recommended Additions:**
```python
# backend/app/utils/observability.py (new file)

import time
import structlog
from contextlib import asynccontextmanager
from typing import AsyncIterator

logger = structlog.get_logger()

@asynccontextmanager
async def trace_node_execution(node_name: str, state: dict) -> AsyncIterator[dict]:
    """
    Trace node execution with structured logging and metrics.
    
    Usage:
        async def my_node(state: AgentState) -> dict:
            async with trace_node_execution("my_node", state) as ctx:
                # ... node logic ...
                ctx["result_count"] = len(results)
            return state_update
    """
    start_time = time.time()
    context = {"node": node_name, "thread_id": state.get("user_id")}
    
    try:
        logger.info("node_start", **context)
        yield context
        
        duration = time.time() - start_time
        logger.info("node_complete", duration_ms=duration * 1000, **context)
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            "node_error",
            error=str(e),
            duration_ms=duration * 1000,
            **context,
            exc_info=True
        )
        raise
```

**Benefits:**
- Better debugging in production
- Performance bottleneck identification
- Easier correlation of logs across nodes

---

### Priority 3: Validation Score Threshold Tuning

**Current Issue:**
```python
# backend/app/agents/nodes/validator.py
if quality_score >= 0.5:  # Recently lowered from 0.7
    return Command(update={...}, goto="__end__")
```

**Recommendation:**
Make threshold configurable per environment:

```python
# backend/app/core/config.py
class Settings(BaseSettings):
    # Validation Configuration
    validation_quality_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Quality score threshold for validation (0.0-1.0)"
    )
    validation_max_retries: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Max validation retries before accepting response"
    )
```

**Use Cases:**
- **Production:** Lower threshold (0.5) for faster responses
- **Research/Demo:** Higher threshold (0.7) for showcase quality
- **A/B Testing:** Different thresholds per user segment

---

### Priority 4: Query Classification Improvements

**Current Implementation:**
```python
# backend/app/agents/nodes/classifier.py
# Uses LLM with structured output for classification
```

**Recommended Enhancement:**
Add few-shot examples to improve classification accuracy:

```python
CLASSIFICATION_EXAMPLES = """
Examples of correct classification:

Query: "hi there!"
→ Type: simple, No retrieval
Reasoning: Greeting, no technical content

Query: "tell me more about that"
→ Type: conversational_followup, Needs retrieval
Reasoning: References previous context ("that")

Query: "what about error handling in async functions?"
→ Type: conversational_followup, Needs retrieval
Reasoning: Follow-up question in conversation

Query: "how do I implement OAuth 2.0 in FastAPI?"
→ Type: complex_standalone, Needs retrieval
Reasoning: Technical question, no context needed

Query: "explain the difference between JWT and session-based auth"
→ Type: complex_standalone, Needs retrieval
Reasoning: New technical topic, requires documentation
"""
```

**Benefits:**
- More accurate routing decisions
- Fewer false positives for retrieval
- Better user experience (faster responses for simple queries)

---

## 🎨 Frontend Improvements

### Priority 1: Type Safety for SSE Events

**Current State:**
```typescript
// frontend/hooks/useChat.ts
// Type assertions without runtime validation
const data = parseEventData(event.data) as TokenEvent
```

**Recommended:**
Use Zod for runtime type validation:

```typescript
// frontend/lib/sse-parser.ts
import { z } from 'zod'

const TokenEventSchema = z.object({
  token: z.string(),
  model: z.string().optional(),
})

const CitationEventSchema = z.object({
  chunk_id: z.string().uuid(),
  document_title: z.string(),
  score: z.number(),
  original_score: z.number().optional(),
  source: z.string(),
  preview: z.string().optional(),
})

export function parseEventData<T>(
  event: MessageEvent,
  schema: z.ZodSchema<T>
): T | null {
  try {
    const parsed = JSON.parse(event.data)
    return schema.parse(parsed)
  } catch (error) {
    console.error('Invalid event data:', error)
    return null
  }
}

// Usage:
const tokenData = parseEventData(event, TokenEventSchema)
if (tokenData) {
  // TypeScript knows tokenData is TokenEvent
  appendToStreamingMessage(tokenData.token)
}
```

**Benefits:**
- Runtime validation prevents crashes
- Better error messages for debugging
- Type safety guaranteed at runtime

---

### Priority 2: Optimistic UI Updates

**Current Behavior:**
User message appears instantly, but waits for server confirmation

**Recommended Pattern:**
```typescript
// frontend/stores/chat-store.ts
import { nanoid } from 'nanoid'

interface OptimisticMessage extends Message {
  status: 'pending' | 'confirmed' | 'failed'
  tempId?: string
}

const sendMessageOptimistic = async (content: string) => {
  const tempId = nanoid()
  
  // 1. Add optimistic message immediately
  addOptimisticMessage({
    id: tempId,
    role: 'user',
    content,
    status: 'pending',
    timestamp: new Date(),
  })
  
  try {
    // 2. Send to server
    const response = await fetch('/api/chat', ...)
    
    // 3. Confirm message with real ID
    confirmMessage(tempId, response.thread_id)
    
  } catch (error) {
    // 4. Mark as failed (show retry option)
    failMessage(tempId, error)
  }
}
```

**Benefits:**
- Instant feedback (no UI lag)
- Better perceived performance
- Handles network failures gracefully

---

### Priority 3: Streaming Performance Monitoring

**Current State:**
Basic token counting in `streamingMetrics`

**Recommended:**
```typescript
// frontend/hooks/useStreamingMetrics.ts
import { useState, useMemo } from 'react'

export function useStreamingMetrics() {
  const [metrics, setMetrics] = useState({
    tokenCount: 0,
    tokensPerSecond: 0,
    firstTokenLatency: null as number | null,
    totalDuration: null as number | null,
    
    // New metrics
    timeToFirstToken: null as number | null,  // TTFT
    interTokenLatency: [] as number[],        // Array of delays between tokens
    chunkSizes: [] as number[],                // Size distribution
  })
  
  // Calculate p50, p95, p99 latencies for monitoring
  const stats = useMemo(() => {
    if (metrics.interTokenLatency.length === 0) {
      return { median: null, p95: null, p99: null }
    }
    
    const sorted = [...metrics.interTokenLatency].sort((a, b) => a - b)
    const n = sorted.length
    
    const getPercentile = (p: number) => {
      const index = Math.floor((p / 100) * (n - 1))
      return sorted[index]
    }
    
    return {
      median: getPercentile(50),
      p95: getPercentile(95),
      p99: getPercentile(99),
    }
  }, [metrics.interTokenLatency])
  
  return { metrics, stats }
}
```

**Use Cases:**
- Performance dashboards
- A/B testing different models
- SLA monitoring

---

### Priority 4: Offline Support & Message Queue

**Current Limitation:**
Network failures lose messages

**Recommended:**
```typescript
// frontend/lib/message-queue.ts
import { nanoid } from 'nanoid'

interface QueuedMessage {
  id: string
  content: string
  threadId: string | null
  timestamp: number
  retries: number
}

export class MessageQueue {
  private queue: QueuedMessage[] = []
  private processing = false
  
  async enqueue(content: string, threadId: string | null) {
    this.queue.push({
      id: nanoid(),
      content,
      threadId,
      timestamp: Date.now(),
      retries: 0,
    })
    
    // Persist to IndexedDB
    await this.persist()
    
    // Try to process immediately
    this.processQueue()
  }
  
  private async processQueue() {
    if (this.processing || !navigator.onLine) return
    
    this.processing = true
    
    while (this.queue.length > 0) {
      const message = this.queue[0]
      
      try {
        await this.sendMessage(message)
        this.queue.shift()  // Remove on success
      } catch (error) {
        message.retries++
        if (message.retries >= 3) {
          this.queue.shift()  // Give up after 3 retries
          this.notifyFailure(message)
        }
        break  // Stop processing on error
      }
    }
    
    this.processing = false
    await this.persist()
  }
}
```

**Benefits:**
- Network resilience
- Better mobile experience
- No lost messages

---

## 🏗️ Architecture Improvements

### Priority 1: Rate Limiting Observability

**Current State:**
Rate limits tracked but not visualized

**Recommended:**
Add `/api/rate-limit/status` endpoint for dashboards:

```typescript
// frontend/app/api/rate-limit/status/route.ts
import { NextResponse } from 'next/server'
import { auth } from '@/lib/auth'
import { apiFetch } from '@/lib/api-client'

export async function GET() {
  const { userId } = await auth()
  
  const status = await apiFetch(`/api/v1/rate-limit/${userId}`)
  
  return NextResponse.json({
    userId,
    limits: {
      chat: { limit: 100, remaining: 87, resetAt: '...' },
      ingest: { limit: 20, remaining: 15, resetAt: '...' },
      documents: { limit: 200, remaining: 198, resetAt: '...' },
    },
    history: [
      { endpoint: 'chat', timestamp: '...', remaining: 88 },
      // ... last 10 requests
    ]
  })
}
```

---

### Priority 2: Document Processing Pipeline

**Current State:**
Synchronous ingestion blocks request

**Recommended:**
Background processing with progress updates:

```python
# backend/app/ingestion/background.py
from celery import Celery
from app.ingestion.pipeline import IngestionPipeline

celery_app = Celery('tasks', broker='redis://localhost:6379')

@celery_app.task(bind=True)
def process_document_async(self, document_id: str, user_id: str):
    """Background document processing with progress updates."""
    pipeline = IngestionPipeline(...)
    
    # Update progress
    self.update_state(
        state='PROCESSING',
        meta={'stage': 'parsing', 'progress': 20}
    )
    
    # ... chunking ...
    self.update_state(
        state='PROCESSING',
        meta={'stage': 'embedding', 'progress': 60}
    )
    
    # ... storing ...
    self.update_state(
        state='SUCCESS',
        meta={'chunks_created': 42, 'progress': 100}
    )
```

**Benefits:**
- Non-blocking uploads
- Real-time progress bars
- Better resource utilization

---

## 📊 Testing & Quality Improvements

### Priority 1: E2E Streaming Tests

**Recommended:**
```python
# backend/tests/test_streaming_e2e.py
import pytest
from app.agents.graph import stream_agent

@pytest.mark.asyncio
async def test_complete_streaming_flow():
    """Test full streaming flow with all event types."""
    events_received = []
    
    async for event in stream_agent(
        query="How do I use Clerk auth?",
        thread_id=None,
        user_id="test_user"
    ):
        events_received.append(event)
    
    # Verify event sequence
    assert events_received[0]["event"] == "agent_start"
    assert any(e["event"] == "token" for e in events_received)
    assert any(e["event"] == "citation" for e in events_received)
    assert events_received[-1]["event"] == "end"
    
    # Verify no duplicate agents
    agent_starts = [e for e in events_received if e["event"] == "agent_start"]
    agent_names = [e["data"]["agent"] for e in agent_starts]
    assert len(agent_names) == len(set(agent_names))
```

---

### Priority 2: Frontend Integration Tests

**Recommended:**
```typescript
// frontend/__tests__/chat-flow.test.tsx
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ChatPage } from '@/app/(dashboard)/chat/page'

describe('Chat Flow', () => {
  it('handles complete streaming conversation', async () => {
    const user = userEvent.setup()
    
    render(<ChatPage />)
    
    // Type message
    const input = screen.getByPlaceholderText(/ask a question/i)
    await user.type(input, 'Hello')
    await user.click(screen.getByRole('button', { name: /send/i }))
    
    // Wait for agent status
    await waitFor(() => {
      expect(screen.getByText(/router/i)).toBeInTheDocument()
    })
    
    // Wait for streaming completion
    await waitFor(() => {
      expect(screen.getByText(/citations/i)).toBeInTheDocument()
    }, { timeout: 10000 })
    
    // Verify message persisted
    expect(screen.getByText('Hello')).toBeInTheDocument()
  })
})
```

---

## 🚀 Performance Optimizations

### Priority 1: Chunk Lazy Loading

**Current:** All chunks loaded in memory

**Recommended:**
```python
# backend/app/retrieval/lazy_chunks.py
import asyncio
from typing import AsyncIterator

async def merge_streams(*tasks) -> AsyncIterator:
    """Merge multiple async iterators, yielding items as they arrive."""
    pending = set(tasks)
    while pending:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            result = await task
            async for item in result:
                yield item

async def retrieve_chunks_streaming(
    query: str,
    user_id: str,
    limit: int = 20
) -> AsyncIterator[SearchResult]:
    """Stream chunks as they're retrieved to reduce latency."""
    
    # Start retrieval immediately
    vector_task = asyncio.create_task(vector_search(query, user_id))
    text_task = asyncio.create_task(text_search(query, user_id))
    
    # Yield chunks as they arrive (don't wait for all)
    async for chunk in merge_streams(vector_task, text_task):
        yield chunk
        if chunk.rank >= limit:
            break
```

---

### Priority 2: Response Caching

**Recommended:**
```python
# backend/app/core/cache.py
import hashlib
from redis import asyncio as aioredis

redis_client = aioredis.from_url('redis://localhost:6379')

async def get_cached_response(query_hash: str) -> str | None:
    """Retrieve cached response from Redis by query hash."""
    return await redis_client.get(f"cache:query:{query_hash}")

async def cache_response(query: str, response: str, ttl: int = 86400):
    """Cache response in Redis with TTL."""
    query_hash = hashlib.sha256(query.encode()).hexdigest()
    await redis_client.setex(
        f"cache:query:{query_hash}",
        ttl,
        response
    )
```

**Use Cases:**
- FAQ queries (same question asked repeatedly)
- Documentation searches (stable content)
- Demo/testing environments

### Priority 3: Frontend Caching (Next.js 15+)

**Current:** Re-fetching threads on every reload/navigation

**Recommended:**
Use `fetch` with `next.revalidate` and cache tags for on-demand invalidation:

```typescript
// frontend/stores/chat-store.ts
const response = await fetch('/api/threads', {
  next: { 
    revalidate: 60, // Cache for 60 seconds (fresh enough for chat lists)
    tags: ['threads'] // Tag for invalidation
  }
})

// frontend/app/api/revalidate/route.ts
import { revalidateTag } from 'next/cache'

export async function POST(req) {
  const { tag } = await req.json()
  revalidateTag(tag) // Purges cache globally
  return NextResponse.json({ revalidated: true })
}
```

**Workflow:**
1. Default: Serve cached thread list (instant load)
2. On Create/Delete/Update: Call `/api/revalidate` with `tag='threads'`
3. Next Request: Fetches fresh data and re-caches

**Benefits:**
- Instant sidebar loading
- Reduced DB load
- Consistent state across tabs

---

## 📝 Documentation Improvements

### Recommended Additions

1. **Architecture Decision Records (ADRs)**
   - `docs/adr/001-langgraph-streaming.md`
   - `docs/adr/002-postgres-checkpointing.md`
   - `docs/adr/003-hybrid-search-rrf.md`

2. **Runbooks**
   - `docs/runbooks/rate-limit-investigation.md`
   - `docs/runbooks/streaming-performance-debug.md`
   - `docs/runbooks/thread-ownership-verification.md`

3. **API Documentation**
   - OpenAPI/Swagger auto-generation
   - Frontend API client auto-generation from schema

---

## 🎯 Migration Plan

### Phase 1: Backend Streaming (Week 1)
- [ ] Update generator node to use `ainvoke()` 
- [ ] Change stream_mode to `["updates", "messages"]`
- [ ] Update SSE event handlers
- [ ] Add E2E streaming tests
- [ ] Deploy to staging

### Phase 2: Frontend Updates (Week 2)
- [ ] Update SSE parser for "messages" events
- [ ] Add Zod validation for events
- [ ] Implement optimistic UI updates
- [ ] Add streaming performance metrics
- [ ] Deploy to staging

### Phase 3: Observability (Week 3)
- [ ] Add structured logging with tracing
- [ ] Create rate limit status endpoint
- [ ] Build admin dashboard
- [ ] Set up alerts

### Phase 4: Performance (Week 4)
- [ ] Implement lazy chunk loading
- [ ] Add response caching
- [ ] Background document processing
- [ ] Load testing & benchmarks

---

## 📈 Success Metrics

### Before (Baseline)
- First token latency: ~2-3s
- Full response time: ~8-12s
- Retry rate: ~15%
- User satisfaction: 72%

### After (Target)
- First token latency: <1.5s ⭐
- Full response time: ~6-8s ⭐
- Retry rate: <5% ⭐
- User satisfaction: >85% ⭐

---

## 🔗 References

- [LangGraph v1 Release Notes](https://docs.langchain.com/oss/python/releases/langgraph-v1)
- [LangGraph Streaming Guide](https://docs.langchain.com/oss/python/langgraph/streaming)
- [Command Pattern Documentation](https://docs.langchain.com/oss/python/langgraph/graph-api)
- [PostgreSQL Checkpointing](https://docs.langchain.com/oss/python/langgraph/persistence)
- [Auto-Streaming Chat Models](https://docs.langchain.com/oss/python/langchain/models)

---

## ✅ Approval

- [ ] Reviewed by Backend Lead
- [ ] Reviewed by Frontend Lead
- [ ] Reviewed by DevOps/Infrastructure
- [ ] Approved for Implementation

**Next Steps:** Create GitHub issues for each priority item and assign to sprints.
