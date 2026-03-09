# Bugfix Plan — Three Critical UX/Functionality Issues

> **Created:** 2026-03-08
> **Status:** Planning — no code changes yet
> **Branch:** `improvements`

---

## Table of Contents

1. [Problem 1: Non-Sequential Citation Numbering](#problem-1-non-sequential-citation-numbering)
2. [Problem 2: Follow-Up Queries Retrieve Wrong Documents](#problem-2-follow-up-queries-retrieve-wrong-documents)
3. [Problem 3: Validator Retry Causes Visible Stream Reset](#problem-3-validator-retry-causes-visible-stream-reset)

---

## Problem 1: Non-Sequential Citation Numbering

### Symptom

The chat response shows citations like `[1], [5], [10]` instead of sequential `[1], [2], [3]`. The gaps confuse users — it looks like sources are missing.

### Root Cause

In `backend/app/agents/nodes/generator.py`, `format_context()` (line 79) uses `enumerate(chunks, 1)` to label all retrieved chunks as "Source 1" through "Source N" (where N can be up to 20). The LLM only references chunks it actually uses in its answer (e.g., Source 1, Source 5, Source 10), skipping the rest. No re-numbering step exists — the `citation_map` is built (lines 303-340) using the original chunk position as keys, and the frontend renders them verbatim.

**Flow:**
```
20 chunks → format_context labels them Source 1..20
  → LLM uses only Source 1, 5, 10 → writes [1], [5], [10]
  → citation_map = {1: {...}, 5: {...}, 10: {...}}
  → Frontend renders [1], [5], [10] as-is
```

### Fix Plan

Add a **post-generation re-numbering step** in `generator_node()` after the LLM response is received and before the return dict is built.

#### Files to Modify

| File | Change |
|------|--------|
| `backend/app/agents/nodes/generator.py` | Add re-numbering logic after line ~302 |

#### Implementation Steps

1. **Extract referenced markers** (already done at line 302):
   ```python
   referenced_markers = {int(m) for m in re.findall(r'\[(\d+)\]', full_response)}
   ```

2. **Build a remapping dict** from original index → sequential index:
   ```python
   sorted_markers = sorted(referenced_markers)
   remap = {old: new for new, old in enumerate(sorted_markers, 1)}
   # e.g. {1: 1, 5: 2, 10: 3}
   ```

3. **Rewrite the response text** — replace `[N]` with `[remap[N]]`:
   ```python
   def renumber_citation(match: re.Match) -> str:
       original = int(match.group(1))
       return f"[{remap.get(original, original)}]"

   full_response = re.sub(r'\[(\d+)\]', renumber_citation, full_response)
   ```

4. **Build citation_map and citations list using remapped indices**:
   ```python
   for idx, chunk in enumerate(chunks, 1):
       if idx in referenced_markers:
           new_idx = remap[idx]
           citation_map[new_idx] = { ... }
           citations.append({"index": new_idx, ...})
   ```

#### Edge Cases

- **Duplicate markers**: `re.findall` already deduplicates via set conversion.
- **No markers referenced**: `remap` is empty, no changes needed — existing code handles this.
- **Markers reference non-existent chunks**: `remap.get(original, original)` preserves the original number as a safe fallback.

#### Testing

- Unit test: given a response with `[1], [5], [10]` and 10 chunks, verify output has `[1], [2], [3]` and `citation_map` keys are `{1, 2, 3}`.
- Integration test: send a query that retrieves 10+ chunks, verify the SSE `citation_map` event has sequential keys.

---

## Problem 2: Follow-Up Queries Retrieve Wrong Documents

### Symptom

User asks "What is the transportation service agreement about?" and gets a correct answer from the correct document. Then asks "can you explain it in more detail?" — the system retrieves completely unrelated documents (SiteHarvester_Report.pdf, thinking_in_langgraph.md, is_prisma_orm_an_orm.md).

### Root Cause

**Conversation context is dropped at the router → query_expander handoff.** The pipeline correctly loads conversation history and classifies the query, but never uses that context to rewrite the vague follow-up before retrieval.

**The context leak visualized:**

| Node | Has conversation context? | What it does with the query |
|------|:---:|---|
| `context_loader` | ✅ | Loads/trims `messages`, builds `conversation_summary` |
| `classifier` | ✅ | Reads `messages[-5:]` via `format_messages_for_classifier()`, correctly classifies as `conversational_followup` with `needs_retrieval=true` |
| `router` | ❌ | Only reads `original_query`. Strips "in more detail" → leaves bare "can you explain it" |
| `query_expander` | ❌ | Only reads `original_query` — never accesses `messages` or `conversation_summary`. Expands "can you explain it" in isolation |
| `retriever` | ❌ | Searches using the disconnected `expanded_queries` → retrieves unrelated docs |

**Key code evidence:**
- `classifier.py` line 87: correctly uses `messages[-5:]` for context
- `query_expander.py` line 194: `query = state.get("original_query")` — **no access to messages or summary**
- `state.py`: `conversation_summary` field exists but is never consumed downstream

The classifier correctly identifies `conversational_followup` and sets `needs_retrieval=true`, which routes to `router` → `query_expander`. But the query_type flag triggers no special handling — it's just metadata.

### Fix Plan

Add a **context-aware query rewriting step** that resolves pronouns and vague references using conversation history before the query reaches the expander/retriever.

#### Option A: New `query_rewriter` Node (Recommended)

Insert a dedicated node between `classifier` and `router` that runs only for `conversational_followup` queries.

#### Option B: Extend `query_expander_node`

Add rewriting logic inside the existing expander when `query_type == "conversational_followup"`.

**Recommendation: Option A** — cleaner separation of concerns, easier to test, and avoids complicating the expander.

#### Files to Modify

| File | Change |
|------|--------|
| `backend/app/agents/nodes/query_rewriter.py` | **New file** — LLM-based pronoun resolution using conversation history |
| `backend/app/agents/nodes/__init__.py` | Export `query_rewriter_node` |
| `backend/app/agents/graph.py` | Add node to graph, update edge from classifier |
| `backend/app/agents/nodes/classifier.py` | Route `conversational_followup` with `needs_retrieval=true` to `query_rewriter` instead of `router` |

#### Implementation Steps

**Step 1: Create `query_rewriter.py`**

```python
@trace_node("query_rewriter")
async def query_rewriter_node(state: AgentState) -> dict:
    """
    Rewrite vague follow-up queries using conversation context.

    Resolves pronouns ("it", "that", "this") and implicit references
    by reading messages and conversation_summary from state.
    """
    original_query = state.get("original_query", "")
    messages = state.get("messages", [])
    conversation_summary = state.get("conversation_summary", "")

    # Format recent conversation for the LLM
    recent_turns = format_recent_turns(messages, max_turns=4)

    # LLM prompt to rewrite the query
    prompt = f"""You are a query rewriting assistant. The user asked a follow-up question
that contains vague references (pronouns like "it", "that", "this", or implicit subjects).

Rewrite the query to be SELF-CONTAINED by resolving all references using the conversation history.

CONVERSATION HISTORY:
{recent_turns}

CONVERSATION SUMMARY (if available):
{conversation_summary or "N/A"}

CURRENT QUERY: {original_query}

REWRITTEN QUERY (self-contained, specific, no pronouns):"""

    rewritten = await llm.ainvoke(prompt)

    return {
        # Write to retrieval_query, not original_query — original_query must remain
        # the unmodified user input (CodeRabbit fix applied 2026-03-08).
        "retrieval_query": rewritten.content.strip(),
        "query_rewritten": True,
    }
```

**Step 2: Update graph edges**

```python
# In classifier.py — route conversational_followup w/ retrieval to query_rewriter
if result.query_type == "conversational_followup" and result.needs_retrieval:
    next_node = "query_rewriter"
elif result.query_type == "simple" or not result.needs_retrieval:
    next_node = "simple_answer"
else:
    next_node = "router"
```

```python
# In graph.py — add node and edge
builder.add_node("query_rewriter", query_rewriter_node)
builder.add_edge("query_rewriter", "router")
```

**Step 3: The rewritten query flows naturally**

After rewriting "can you explain it in more detail" → "can you explain the transportation service agreement in more detail", the existing `router` → `query_expander` → `retriever` pipeline will work correctly because the query now has specific keywords.

#### Updated Graph Flow

```
START → context_loader → classifier
  ├─ simple/no-retrieval         → simple_answer → END
  ├─ conversational_followup     → query_rewriter → router → ...
  └─ complex_standalone          → router → ...
                                     ├─ simple     → retriever
                                     ├─ complex    → query_expander → retriever
                                     └─ ambiguous  → query_expander → retriever
                                                       ↓
                                              retriever → generator → validator
                                                                        ├─ pass → END
                                                                        └─ fail → query_expander (retry)
```

#### Edge Cases

- **Follow-up that doesn't need retrieval** (e.g., "thanks for that"): Already handled — classifier routes to `simple_answer` when `needs_retrieval=false`.
- **Follow-up with no prior context** (first message is vague): The rewriter should detect no conversation history and pass the query through unchanged. Add a guard: if `len(messages) <= 1`, skip rewriting.
- **Rewriter produces worse query**: Log both original and rewritten queries. Add a config flag `ENABLE_QUERY_REWRITER` to disable in production if needed.

#### Testing

- Unit test: given messages = ["What is the transportation service agreement about?", AI response, "can you explain it in more detail?"], verify rewritten query contains "transportation service agreement".
- Integration test: run the full pipeline with a follow-up query, verify `retrieved_chunks` come from the correct document.

---

## Problem 3: Validator Retry Causes Visible Stream Reset

### Symptom

When the validator rejects a generated response (score < 0.5), the user sees:
1. Full answer streams in (5+ seconds of visible tokens)
2. Answer instantly disappears (frontend clears content)
3. New answer starts streaming from scratch
4. Cycle repeats up to 3 times (initial + 2 retries)

This creates a jarring UX — the user reads partial content that vanishes.

### Root Cause

**Tokens stream to the client DURING generation, but validation runs AFTER generation completes.** By the time the validator decides to reject, all tokens have already been displayed.

**The timeline:**
```
0s    Generator starts (ainvoke with stream_mode="messages")
0-5s  Tokens stream to client → user sees full answer forming
5s    Generator completes, validator starts
5-6s  LLM scoring → score 0.45 → FAIL
6s    Backend emits token_reset SSE event (graph.py lines 416-425)
6s    Frontend resetStreamingMessage() clears content (useChat.ts lines 156-161)
6s    Graph loops: validator → query_expander → retriever → generator (retry)
6-12s Second attempt streams... potentially rejected again
```

**Key code locations:**
- `graph.py` lines 416-425: Emits `TokenResetEvent` when `retry_count > 0` in validator update
- `useChat.ts` lines 156-161: Handles `token_reset` by calling `resetStreamingMessage()`
- `validator.py` line 32: `MAX_RETRIES = settings.validation_max_retries` (default 2)
- `validator.py` lines 207-220: Returns `Command(goto="query_expander", update={"retry_count": retry_count + 1})`

### Fix Plan: Silent Generation + Validate + Stream (Approach 1 + 4)

**Core idea:** Generate the full response **without streaming to the client**, validate it, and only stream the final approved response. Show a "thinking" indicator during the hidden generation + validation phase.

#### Architecture Change

```
BEFORE (current — tokens leak before validation):
  Generator (ainvoke + auto-stream tokens) → Validator (too late)
                     ↑ user sees tokens here

AFTER (proposed — buffer + validate + stream):
  Generator (silent, buffered) → Validator → Stream approved response
                                               ↑ user sees tokens here
  [thinking indicator shown]                 [thinking hidden, tokens appear]
```

#### Files to Modify

| File | Change |
|------|--------|
| `backend/app/agents/nodes/generator.py` | Split into two modes: silent generation + streaming flush |
| `backend/app/agents/graph.py` | Restructure streaming logic to buffer generator tokens |
| `backend/app/schemas/events.py` | Add `ThinkingEvent` SSE event type |
| `frontend/hooks/useChat.ts` | Handle `thinking` SSE events, show/hide indicator |
| `frontend/stores/chat-store.ts` | Add `isThinking` state |
| `frontend/components/chat/` | Add thinking indicator UI component |

#### Implementation Steps

**Step 1: Add new SSE event types**

In `backend/app/schemas/events.py`:
```python
class SSEEventType(str, Enum):
    # ... existing events ...
    THINKING = "thinking"           # Show thinking indicator
    BUFFERED_TOKENS = "buffered_tokens"  # Flush approved tokens

class ThinkingEvent(BaseModel):
    status: Literal["start", "validating", "retrying", "complete"]
    message: str
    attempt: int = 1
    max_attempts: int = 3
```

**Step 2: Restructure `stream_agent()` in `graph.py`**

The key change is to **buffer tokens from the generator node** instead of yielding them immediately, then flush the buffer only after the validator passes.

```python
# Pseudocode for the restructured streaming logic

token_buffer: list[str] = []
buffering = False  # True when inside generator node

async for chunk in graph_instance.astream(...):
    mode, data = chunk

    if mode == "updates":
        node_name = next(iter(data.keys()))
        node_update = data[node_name]

        if node_name == "generator":
            # Generator completed — do NOT flush tokens yet
            # They stay in buffer until validator approves
            buffering = False

        if node_name == "validator":
            validation = node_update.get("validation_result", {})

            if validation.get("passed"):
                # APPROVED — flush buffered tokens to client
                yield ThinkingEvent(status="complete", ...)
                for token in token_buffer:
                    yield TokenEvent(token=token, ...)
                yield CitationMapEvent(...)  # emit citation map
                token_buffer.clear()
            elif node_update.get("retry_count", 0) > 0:
                # REJECTED — discard buffer, emit retry indicator
                token_buffer.clear()
                yield ThinkingEvent(status="retrying", attempt=retry_count, ...)
                # No token_reset needed — buffer was never shown to user

    elif mode == "messages":
        msg_chunk, metadata = data
        if metadata.get("langgraph_node") == "generator":
            if msg_chunk.content:
                # BUFFER instead of yielding
                token_buffer.append(msg_chunk.content)
        elif metadata.get("langgraph_node") == "simple_answer":
            # Simple answers bypass validation — stream directly
            yield TokenEvent(token=msg_chunk.content, ...)
```

**Step 3: Token flushing strategy**

When the validator passes, flush buffered tokens to the client. Two options:

- **Option A: Instant flush** — Emit all tokens in a rapid batch. Response appears "instantly" after thinking completes. Simplest implementation.
- **Option B: Simulated streaming** — Emit tokens with small delays (~5-10ms) to preserve the streaming feel. Better UX but adds minor latency.

**Recommendation: Option A** (instant flush). Users prefer fast results over artificial streaming animations, and the thinking indicator already manages expectations.

**Step 4: Frontend thinking indicator**

In `frontend/hooks/useChat.ts`, handle the new `thinking` event:
```typescript
case 'thinking': {
    const thinking = JSON.parse(event.data) as ThinkingEvent
    setThinkingStatus(thinking)  // Update store
    break
}
```

In `frontend/stores/chat-store.ts`, add thinking state:
```typescript
interface ChatState {
    // ... existing state ...
    thinkingStatus: ThinkingEvent | null
    setThinkingStatus: (status: ThinkingEvent | null) => void
}
```

In the chat message component, show a thinking indicator when `thinkingStatus` is active:
```
┌─────────────────────────────────────┐
│  🔄 Analyzing and verifying...      │
│  Quality check in progress (1/3)    │
└─────────────────────────────────────┘
```

The indicator updates its message based on `ThinkingEvent.status`:
- `"start"` → "Generating response..."
- `"validating"` → "Verifying response quality..."
- `"retrying"` → "Improving response (attempt 2/3)..."
- `"complete"` → indicator fades/hides, tokens start flowing

**Step 5: Remove token_reset handling**

Since tokens are never shown before validation, the `token_reset` event is no longer needed. However, keep the event type for backward compatibility and remove it in a future cleanup.

- `graph.py`: Remove the `TokenResetEvent` emission block (lines 416-425)
- `useChat.ts`: Keep the `token_reset` handler as a no-op fallback

#### Performance Considerations

- **Latency impact**: Users will wait for full generation + validation (~6-7s) before seeing any tokens. The thinking indicator mitigates perceived latency.
- **Retry latency**: Each retry adds another ~6-7s of hidden generation. With 2 retries, worst case is ~20s before first visible token. Consider lowering `MAX_RETRIES` to 1 for most queries.
- **Memory**: Buffering full responses in memory is negligible (~2-5KB per response).

#### Edge Cases

- **Validator passes on first attempt** (happy path, ~90% of cases): User sees thinking indicator for ~6s, then instant response. Acceptable tradeoff.
- **All retries exhausted**: Validator returns with disclaimer. Flush the last attempt's buffer (the best we have) with the disclaimer appended. User still gets a response.
- **Generator fails (exception)**: Error propagates normally through graph. No tokens buffered = nothing to flush.
- **Simple answers (no validation)**: `simple_answer` node bypasses the validator entirely. Tokens stream directly as today — no buffering, no thinking indicator.

#### Testing

- Unit test: Mock a validator that fails once then passes. Verify only one set of tokens reaches the client (no duplicates, no resets).
- Integration test: Send a query that triggers validation retry. Verify:
  1. `thinking` events are emitted with correct status progression
  2. No `token_reset` events are emitted
  3. Final tokens arrive after `thinking: complete`
  4. `citation_map` arrives after tokens
- Frontend test: Verify the thinking indicator shows/hides, and content doesn't flash.

---

## Implementation Priority & Order

| Priority | Problem | Effort | Impact |
|----------|---------|--------|--------|
| 1st | **Problem 1** — Citation re-numbering | Small (1 file, ~20 lines) | High — every response looks broken |
| 2nd | **Problem 2** — Query rewriter node | Medium (new node + graph edges) | High — follow-ups are core UX |
| 3rd | **Problem 3** — Silent generation + thinking | Large (backend streaming + frontend UI) | Medium — only affects failed validations |

### Dependencies

- Problem 1 and Problem 2 are independent — can be done in parallel.
- Problem 3 is independent but should be done last (most complex, touches streaming architecture).
- All three should be on the `improvements` branch.
