# Token-by-Token Streaming Implementation

## Overview

Implemented **true token-by-token streaming** for the LLM generator node. Previously, the system only streamed the complete response after generation. Now, each token is streamed to the frontend as it's received from the OpenAI API, enabling a ChatGPT-like typing effect.

## Changes Made

### 1. Generator Node (`backend/app/agents/nodes/generator.py`)

**Key Changes:**

- Added `get_stream_writer()` from `langgraph.config` to emit custom events
- Modified token streaming loop to emit each token via `writer()` as it arrives
- Writer emits custom events with structure: `{"type": "token", "token": <token_text>, "model": <model_name>}`
- Maintains full response accumulation for accurate token counting and metadata
- Gracefully handles non-streaming mode (when `writer` is `None`)

**Code Flow:**

```python
from langgraph.config import get_stream_writer

async def generator_node(state: AgentState) -> dict:
    # Get stream writer (only available in streaming mode)
    writer = None
    try:
        writer = get_stream_writer()
    except Exception:
        pass  # No writer available (non-streaming mode)

    # Stream tokens from LLM
    async for chunk in llm.astream(messages):
        if chunk.content:
            token = chunk.content
            full_response += token

            # Emit token event for real-time streaming
            if writer:
                writer({
                    "type": "token",
                    "token": token,
                    "model": settings.openai_model,
                })
```

### 2. Graph Streaming (`backend/app/agents/graph.py`)

**Key Changes:**

- Updated `stream_agent()` to use **combined streaming modes**: `stream_mode=["updates", "custom"]`
- Changed from `astream_events()` to `astream()` with dual modes for better performance
- Added handler for `("custom", data)` events from nodes
- Parses custom events and emits SSE `TokenEvent` for each token

**Code Flow:**

```python
async for chunk in graph.astream(
    initial_state,
    config=config,
    stream_mode=["updates", "custom"],  # Dual mode streaming
):
    mode, data = chunk

    if mode == "updates":
        # Handle node state updates (existing logic)
        ...

    elif mode == "custom":
        # Handle custom events from nodes (NEW)
        if isinstance(data, dict) and data.get("type") == "token":
            yield {
                "event": SSEEventType.TOKEN.value,
                "data": TokenEvent(
                    token=data.get("token", ""),
                    model=data.get("model"),
                ).model_dump_json()
            }
```

## How It Works

### LangGraph Custom Streaming

LangGraph supports **custom streaming** via `get_stream_writer()`:

- Nodes can emit arbitrary data during execution
- Use `stream_mode="custom"` or combine with other modes (`["updates", "custom"]`)
- Writer is automatically injected when streaming is enabled
- Safe to call `get_stream_writer()` in non-streaming contexts (returns `None`)

Reference: [LangGraph Custom Streaming Docs](https://docs.langchain.com/oss/python/langgraph/streaming)

### Event Flow

1. **Frontend** → POST `/api/v1/chat` with `stream=true`
2. **API** → Calls `stream_agent(query)`
3. **Graph** → Executes nodes with `stream_mode=["updates", "custom"]`
4. **Generator Node** →
   - Calls `llm.astream(messages)` to stream from OpenAI
   - For each token received, calls `writer({"type": "token", "token": <token>})`
5. **Graph** → Catches custom events and yields them
6. **API** → Converts to SSE format and sends to frontend
7. **Frontend** → Accumulates tokens and displays progressive response

### SSE Event Format

```
event: token
data: {"token": "To", "model": "gpt-4o-mini"}

event: token
data: {"token": " integrate", "model": "gpt-4o-mini"}

event: token
data: {"token": " Clerk", "model": "gpt-4o-mini"}
...
```

## Testing

### 1. Via Test Script

```bash
cd backend
uv run python scripts/test_token_streaming.py
```

**Expected Output:**

```
================================================================================
TOKEN-BY-TOKEN STREAMING TEST
================================================================================
OpenAI Model: gpt-4o-mini
Test Query: 'What is Clerk?'
================================================================================

[ROUTER] Executing router node
[RETRIEVER] Executing retriever node
[GENERATOR] Executing generator node

⚡ FIRST TOKEN received in 2.145s
Model: gpt-4o-mini
--------------------------------------------------------------------------------
STREAMING RESPONSE:

To integrate Clerk with your application, first install...
[tokens stream character by character]

[VALIDATION] ✓ Passed (score: 0.92)
[END] ✓ Success

================================================================================
STREAMING TEST RESULTS
================================================================================
Total Time: 8.234s
Time to First Token: 2.145s
Tokens Streamed: 156
Streaming Duration: 5.834s
Tokens/Second: 26.7
Response Length: 847 characters

✓ Token-by-token streaming SUCCESSFUL!
```

### 2. Via cURL

```bash
cd backend
./scripts/test_chat_curl.sh streaming
```

**Expected Output:**

```
[EVENT] token
[DATA] {"token": "To", "model": "gpt-4o-mini"}

[EVENT] token
[DATA] {"token": " integrate", "model": "gpt-4o-mini"}

[EVENT] token
[DATA] {"token": " Clerk", "model": "gpt-4o-mini"}
...
```

### 3. Via Frontend

Start the backend and frontend, then:

1. Navigate to chat interface
2. Send a message
3. **Observe:** Response appears word-by-word as tokens stream (like ChatGPT)

## Performance Impact

### Before (Full Response Streaming)

- **Time to First Token:** ~10-11s (entire response ready)
- **User Experience:** Long wait, then entire response appears
- **Perceived Latency:** Very high (no feedback until complete)

### After (Token-by-Token Streaming)

- **Time to First Token:** ~2-3s (just router + retriever + LLM first token)
- **User Experience:** Immediate progressive feedback
- **Perceived Latency:** Much lower (feels instant)
- **Network:** More events but smaller payload per event
- **Total Time:** Same or slightly faster (~10-11s total)

## Backward Compatibility

✅ **Non-Streaming Mode Still Works:**

- When `stream=false`, `get_stream_writer()` returns `None`
- Generator node accumulates full response as before
- Token counting and metadata remain accurate

✅ **All Other Nodes Unchanged:**

- Router, retriever, validator nodes work exactly as before
- Only generator node modified for token emission

## Frontend Integration

### Current SSE Handler (Needs Update)

If frontend already handles `token` events:

- ✅ Should work immediately (events now arrive incrementally)
- Verify token accumulation logic handles partial responses

If frontend only expects one complete response:

- ⚠️ Update to accumulate tokens:

```typescript
// Before (expecting one complete response)
case 'token':
  setResponse(event.data.token);  // Replaces entire response
  break;

// After (accumulating tokens)
case 'token':
  setResponse(prev => prev + event.data.token);  // Appends token
  break;
```

## Configuration

No new environment variables needed. Existing config controls behavior:

```env
# Use fast model for quick token streaming
OPENAI_MODEL="gpt-4o-mini"

# LangSmith tracing (optional, shows token events)
LANGCHAIN_TRACING_V2="true"
LANGCHAIN_PROJECT="integration-forge"
```

## Debugging

### Enable Verbose Logging

```env
LOG_LEVEL="DEBUG"
```

### Check Token Events

Look for logs:

```
⏱️  GENERATOR NODE: Starting LLM response generation
  ↳ LLM generation took 5.234s
⏱️  GENERATOR NODE: Completed in 5.421s | Tokens: 156 (42 prompt + 114 completion)
```

### Verify Custom Events

```python
# In generator_node (temporary debug)
if writer:
    logger.debug(f"Emitting token: {token!r}")
    writer({"type": "token", "token": token, "model": settings.openai_model})
```

## Troubleshooting

### Issue: No tokens received

**Cause:** `stream_mode` not configured correctly
**Fix:** Ensure `stream_agent()` uses `stream_mode=["updates", "custom"]`

### Issue: Tokens arrive in batches

**Cause:** OpenAI API may batch small tokens
**Expected:** Normal behavior for short tokens like punctuation
**Mitigation:** N/A (controlled by OpenAI streaming)

### Issue: Frontend shows duplicated text

**Cause:** Frontend appends token twice (once in accumulator, once in display)
**Fix:** Ensure UI only displays the accumulated state, not individual token events

## Next Steps

### Optional Enhancements

1. **Token Timing Metrics**
   - Track time between tokens for latency monitoring
   - Add `timestamp` to token events

2. **Partial Markdown Rendering**
   - Stream tokens through markdown parser incrementally
   - Handle code blocks and formatting during streaming

3. **Token Batching**
   - Batch N tokens before emitting (reduce event count)
   - Trade-off: fewer events vs. slightly higher latency

4. **Cancellation Support**
   - Add ability to cancel streaming mid-response
   - Requires frontend cancel button + backend abort logic

## References

- [LangGraph Custom Streaming](https://docs.langchain.com/oss/python/langgraph/streaming)
- [LangChain Streaming Guide](https://docs.langchain.com/oss/python/langchain/streaming)
- [OpenAI Streaming API](https://platform.openai.com/docs/api-reference/streaming)
- [Server-Sent Events (SSE)](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)

## Summary

✅ **Implemented true token-by-token streaming**  
✅ **Uses LangGraph custom streaming with `get_stream_writer()`**  
✅ **Backward compatible with non-streaming mode**  
✅ **Maintains accurate token counting and metadata**  
✅ **Ready to test with existing test scripts**  
🎯 **Next:** Test frontend integration and verify token accumulation logic
