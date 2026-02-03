# LangGraph Checkpointer Lifecycle Fix

## Problem

The backend was experiencing `psycopg.OperationalError: the connection is closed` errors because the checkpointer's async context manager lifecycle was being managed incorrectly.

## Root Cause

The `get_graph()` function was creating a checkpointer context manager and entering it, but never exiting it properly. This caused the database connection to eventually close, leading to errors.

## Solution

Moved checkpointer initialization to FastAPI's lifespan events and passed the checkpointer instance through the application state.

## Files Modified

### 1. `backend/app/core/config.py`

- Added `enable_checkpointing: bool = True` setting
- Allows easy toggle of checkpointing via `ENABLE_CHECKPOINTING` env var

### 2. `backend/app/agents/graph.py`

- **REMOVED**: Broken `async def get_graph()` with context manager lifecycle issues
- **ADDED**: Simple `def get_graph(checkpointer=None)` that accepts checkpointer as parameter
- **UPDATED**: All agent functions (`run_agent`, `stream_agent`, `get_checkpoint`, `resume_agent`) now accept optional `checkpointer` parameter

### 3. `backend/app/main.py`

- **UPDATED**: `lifespan()` function to:
  - Initialize checkpointer on startup if `enable_checkpointing=True`
  - Call `checkpointer.setup()` to create tables (idempotent)
  - Store checkpointer instance in `app.state.checkpointer`
  - Properly exit context manager on shutdown

### 4. `backend/app/api/v1/chat.py`

- **UPDATED**: Chat endpoint to pass `request.app.state.checkpointer` to `stream_agent()`

## How It Works

### Startup Flow:

1. FastAPI starts → `lifespan()` context manager entered
2. If `ENABLE_CHECKPOINTING=true`:
   - Create `AsyncPostgresSaver.from_conn_string()` context manager
   - Enter context to get checkpointer instance
   - Call `await checkpointer.setup()` (creates tables if needed)
   - Store in `app.state.checkpointer`
3. Application runs with single, persistent checkpointer instance

### Request Flow:

1. Chat request arrives
2. Get checkpointer from `request.app.state.checkpointer`
3. Pass to `stream_agent(checkpointer=checkpointer)`
4. `get_graph(checkpointer)` compiles graph with checkpointer
5. Graph executes with proper checkpointing

### Shutdown Flow:

1. FastAPI shutdown signal
2. `lifespan()` cleanup executes
3. Exit checkpointer context manager (`__aexit__`)
4. Database connection properly closed

## Benefits

✅ Single checkpointer instance for entire app lifecycle  
✅ Proper connection management (no leaks)  
✅ Can toggle checkpointing via env var  
✅ Full conversation persistence support  
✅ Clean shutdown without errors

## Testing

To test the fix:

```bash
# Start backend
cd backend
uvicorn app.main:app --reload

# Send a chat request
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT" \
  -d '{"message": "Hello"}'
```

## Disabling Checkpointing (Optional)

If you want to temporarily disable checkpointing for testing:

```bash
# Add to backend/.env
ENABLE_CHECKPOINTING=false
```

## Next Steps

- Monitor logs for checkpointer initialization messages
- Verify no more "connection is closed" errors
- Test conversation persistence across sessions
- Consider adding checkpointer health check endpoint
