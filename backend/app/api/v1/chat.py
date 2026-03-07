"""
Chat/query endpoint with SSE streaming.

This module provides the chat endpoint that integrates with the agentic RAG system
from Phase 4, supporting both streaming (SSE) and non-streaming responses.

Phase 6 Production Enhancements:
- Rate limiting on streaming endpoint
- Token validation and XSS protection
- Client disconnect detection
- Stream observability metrics
"""

import asyncio
import hashlib
import json
import time
from typing import AsyncIterator
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.agents.graph import run_agent, stream_agent
from app.api.deps import UserID, RateLimitInfo
from app.core.config import settings
from app.database.pool import DatabasePool
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.events import SSEEventType
from app.utils.logger import get_logger
from app.utils.metrics import StreamMetrics
from app.utils.stream_validator import TokenValidator, validate_citation_content

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


# ============================================================================
# Privacy-Safe Logging Helper
# ============================================================================


def get_message_hash(message: str) -> str:
    """
    Generate a privacy-safe hash of the user message for logging.

    Uses SHA-256 to create a deterministic hash that:
    - Allows correlation of identical messages in logs
    - Protects user privacy (PII not exposed)
    - Cannot be reversed to recover original text

    In development: Returns first 16 chars of hash for readability
    In production: Returns full 64-char hash for maximum uniqueness

    Args:
        message: The user's message text

    Returns:
        Hexadecimal hash string (16 or 64 chars)

    Learning Note:
    Why hash instead of truncate?
    - Truncation can leak PII (names, emails, addresses)
    - Hash is one-way (cannot recover original)
    - Deterministic (same message = same hash = correlation)
    - GDPR/privacy compliant (no personal data stored)
    """
    # Create SHA-256 hash of the full message
    hash_obj = hashlib.sha256(message.encode('utf-8'))
    full_hash = hash_obj.hexdigest()

    # In development, use shorter hash for readability
    # In production, use full hash for uniqueness
    if settings.environment == "development":
        return full_hash[:16]  # First 16 chars (64 bits)
    else:
        return full_hash  # Full 64 chars (256 bits)


# ============================================================================
# SSE Helper Functions
# ============================================================================


async def sse_generator(
    query: str,
    thread_id: str,
    user_id: str,
    request: Request,
    is_new_thread: bool = False,
    custom_title: str | None = None,
) -> AsyncIterator[str]:
    """
    Generate Server-Sent Events (SSE) from the agent stream.

    SSE format:
        event: <event_type>
        data: <json_data>

        (blank line separator)

    Features:
    - Token validation and sanitization
    - Citation content validation
    - Client disconnect detection
    - Stream observability metrics

    Args:
        query: User's question
        thread_id: Thread ID for conversation
        user_id: User identifier
        request: FastAPI request object (for disconnect detection)

    Yields:
        Formatted SSE strings
    """
    # Initialize metrics
    metrics = StreamMetrics(
        user_id=user_id,
        thread_id=str(thread_id) if thread_id else "unknown",
    )
    start_time = time.time()
    metrics.record_connection_success((time.time() - start_time) * 1000)

    # Initialize validator
    validator = TokenValidator()

    # Track successful completion for thread_created event
    stream_successful = False
    # Will hold the asyncio Task for LLM title generation (new threads only)
    title_task: asyncio.Task[str] | None = None

    try:
        # Get checkpointer from app state (may be None in tests without lifespan)
        checkpointer = getattr(request.app.state, "checkpointer", None)

        # Kick off LLM title generation in parallel with the main astream loop so it
        # never adds latency to token delivery.
        if is_new_thread:
            from app.utils.title_generator import generate_title
            title_task = asyncio.create_task(generate_title(query))

        # Send thread_created event for new threads IMMEDIATELY (before streaming)
        # This allows frontend to redirect to /chat/[threadId] before tokens arrive
        if is_new_thread:
            thread_created_event = {
                "event": "thread_created",
                "data": json.dumps({"thread_id": str(thread_id)})
            }
            yield f"event: {thread_created_event['event']}\ndata: {thread_created_event['data']}\n\n"
            logger.info(
                "Thread created event sent",
                extra={"user_id": user_id, "thread_id": str(thread_id)}
            )

        async for event in stream_agent(query, thread_id, user_id, checkpointer=checkpointer):
            # Check for client disconnect
            if await request.is_disconnected():
                logger.info(
                    "Client disconnected, stopping stream",
                    extra={"user_id": user_id, "thread_id": str(thread_id)}
                )
                metrics.record_disconnect()
                break

            # Event structure: {"event": "event_type", "data": "json_string"}
            event_type = event.get("event", "unknown")
            event_data_str = event.get("data", "{}")

            # Parse event data for validation
            try:
                event_data = json.loads(event_data_str)
            except json.JSONDecodeError:
                logger.warning(
                    "Failed to parse event data",
                    extra={"user_id": user_id, "event_type": event_type}
                )
                continue

            # Validate based on event type
            if event_type == SSEEventType.TOKEN.value:
                token = event_data.get("token", "")
                is_valid, error_msg = validator.validate_token(token, user_id)
                if not is_valid:
                    logger.warning(
                        "Invalid token blocked",
                        extra={"user_id": user_id, "error": error_msg}
                    )
                    metrics.record_error(f"Invalid token: {error_msg}")
                    continue
                metrics.record_token(token)

            elif event_type == SSEEventType.CITATION.value:
                chunk_id = event_data.get("chunk_id", "")
                doc_title = event_data.get("document_title", "")
                content = event_data.get("preview", "")
                is_valid, error_msg = validate_citation_content(
                    chunk_id, doc_title, content, user_id
                )
                if not is_valid:
                    logger.warning(
                        "Invalid citation blocked",
                        extra={"user_id": user_id, "error": error_msg}
                    )
                    metrics.record_error(f"Invalid citation: {error_msg}")
                    continue
                metrics.record_citation()

            elif event_type == SSEEventType.AGENT_START.value:
                agent = event_data.get("agent", "unknown")
                metrics.record_agent_start(agent)

            elif event_type == SSEEventType.AGENT_COMPLETE.value:
                agent = event_data.get("agent", "unknown")
                duration = event_data.get("duration_ms", 0)
                metrics.record_agent_complete(agent, duration)

            # Format as SSE
            sse_message = f"event: {event_type}\ndata: {event_data_str}\n\n"
            yield sse_message

            # Small delay to allow disconnect detection
            await asyncio.sleep(0)

        # Mark stream as successful if we completed without errors
        stream_successful = True

        # ------------------------------------------------------------------
        # Emit thread_title SSE event and persist the LLM-generated title
        # ------------------------------------------------------------------
        if title_task is not None:
            from app.schemas.events import ThreadTitleEvent
            try:
                title = await asyncio.wait_for(title_task, timeout=10.0)
                title_task = None  # Mark as consumed
            except (asyncio.TimeoutError, Exception):
                logger.warning(
                    "Title generation failed or timed out, using fallback",
                    extra={"thread_id": str(thread_id)},
                )
                title = query.strip()[:50]
                title_task = None

            yield (
                f"event: {SSEEventType.THREAD_TITLE.value}\n"
                f"data: {ThreadTitleEvent(title=title, thread_id=str(thread_id)).model_dump_json()}\n\n"
            )

            # Persist the title to checkpoint metadata so the threads listing
            # picks it up immediately without any client-side PATCH request.
            # Uses the shared DatabasePool (opened at app lifespan) — no new
            # connection is opened, and the ownership filter (user_id) ensures
            # a compromised thread_id cannot overwrite another user's title.
            try:
                async with DatabasePool.get_connection() as conn:
                    async with conn.cursor() as cur:
                        # Scope the statement timeout to this transaction only
                        await cur.execute("SET LOCAL statement_timeout = '30s'")
                        await cur.execute(
                            """
                            UPDATE checkpoints
                            SET metadata = jsonb_set(
                                COALESCE(metadata, '{}'::jsonb),
                                '{custom_title}',
                                to_jsonb(%s::text)
                            )
                            WHERE thread_id = %s
                              AND checkpoint->'channel_values'->>'user_id' = %s
                            """,
                            (title, str(thread_id), user_id),
                        )
                logger.info(
                    "Thread title persisted",
                    extra={"thread_id": str(thread_id), "title": title},
                )
            except Exception as persist_err:
                logger.warning(
                    "Failed to persist thread title",
                    extra={"thread_id": str(thread_id), "error": str(persist_err)},
                )

    except asyncio.CancelledError:
        logger.info(
            "Stream cancelled",
            extra={"user_id": user_id, "thread_id": str(thread_id)}
        )
        metrics.record_cancel()
        raise

    except Exception as e:
        logger.error(
            "Error in SSE stream",
            extra={"error": str(e), "user_id": user_id},
            exc_info=True
        )
        metrics.record_error(str(e))

        # Send error event
        error_event = {
            "event": SSEEventType.AGENT_ERROR.value,
            "data": json.dumps({
                "error": str(e),
                "message": "Stream encountered an error"
            })
        }
        yield f"event: {error_event['event']}\ndata: {error_event['data']}\n\n"

        # Send end event
        end_event = {
            "event": SSEEventType.END.value,
            "data": json.dumps({"done": True, "error": True})
        }
        yield f"event: {end_event['event']}\ndata: {end_event['data']}\n\n"

    finally:
        # Cancel title task if still running (e.g., client disconnected mid-stream)
        if title_task is not None and not title_task.done():
            title_task.cancel()
        # thread_created event now sent at stream start (not here)
        # Finalize and log metrics
        metrics.finalize()
        logger.debug(
            "Stream metrics",
            extra={"metrics": metrics.to_dict()}
        )


# ============================================================================
# Endpoints
# ============================================================================


@router.post(
    "",
    summary="Chat with the agentic RAG system",
    description="Send a message and get an AI-generated response using agentic retrieval-augmented generation",
)
async def chat(
    chat_request: ChatRequest,
    user_id: UserID,
    rate_limit_info: RateLimitInfo,
    request: Request,
):
    """
    Chat endpoint with support for both streaming and non-streaming responses.

    **Streaming Mode (stream=true, default):**
    - Returns Server-Sent Events (SSE)
    - Real-time progress updates
    - Events: agent_start, progress, citation, token, validation, end
    - Content-Type: text/event-stream

    **Non-Streaming Mode (stream=false):**
    - Returns complete ChatResponse JSON
    - Blocks until agent completes
    - Content-Type: application/json

    Phase 5: Uses hardcoded user_id from dependency
    Phase 6: Will use JWT-authenticated user_id

    Args:
        request: ChatRequest with message and options
        user_id: Current user ID (injected via dependency)

    Returns:
        StreamingResponse (SSE) if stream=true
        ChatResponse (JSON) if stream=false

    Raises:
        HTTPException: 422 for validation errors
        HTTPException: 500 for agent execution errors
    """
    logger.info(
        "Chat request received",
        extra={
            "user_id": user_id,
            "message_hash": get_message_hash(chat_request.message),
            "stream": chat_request.stream,
            "thread_id": str(chat_request.thread_id) if chat_request.thread_id else "new",
        }
    )

    # Thread ID resolution:
    # - Legacy path: client sends thread_id=None → backend generates UUID
    # - Modern path: client pre-generates UUID and sends is_new_thread=True
    if chat_request.thread_id is None:
        thread_id = str(uuid4())
        is_new_thread = True
        logger.info(
            "Creating new thread (legacy: backend-generated ID)",
            extra={"user_id": user_id, "thread_id": thread_id}
        )
    else:
        thread_id = str(chat_request.thread_id)  # Convert UUID to string
        # Trust the client flag — client pre-generated the ID for new threads
        is_new_thread = chat_request.is_new_thread
        if is_new_thread:
            logger.info(
                "Creating new thread (client-generated ID)",
                extra={"user_id": user_id, "thread_id": thread_id}
            )
            # Security: verify the claimed-new thread ID truly has no existing state.
            # Without this check a malicious client could supply an existing thread's
            # UUID with is_new_thread=True to bypass the ownership check below and
            # overwrite another user's conversation.
            verify_checkpointer = getattr(request.app.state, "checkpointer", None)
            if verify_checkpointer is not None:
                try:
                    from app.agents.graph import get_graph
                    graph_instance = get_graph(verify_checkpointer)
                    existing_state = await graph_instance.aget_state(
                        config={"configurable": {
                            "thread_id": thread_id, "checkpoint_ns": ""}},
                        subgraphs=False,
                    )
                    if existing_state.values:
                        logger.warning(
                            "Client claimed is_new_thread=True for an existing thread ID",
                            extra={"user_id": user_id, "thread_id": thread_id}
                        )
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="Thread ID already exists; use a different ID for a new thread.",
                        )
                except HTTPException:
                    raise
                except Exception as e:
                    logger.error(
                        "Error checking thread existence for new-thread claim",
                        extra={"user_id": user_id, "thread_id": thread_id, "error": str(e)},
                        exc_info=True,
                    )
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Unable to verify thread ID uniqueness; please retry.",
                    )
        else:
            logger.debug(
                "Using existing thread",
                extra={"user_id": user_id, "thread_id": thread_id}
            )

    # Ownership verification for existing threads
    if not is_new_thread:
        # Get checkpointer from app state (may be None in tests without lifespan)
        checkpointer = getattr(request.app.state, "checkpointer", None)

        if checkpointer is None:
            # Checkpointer unavailable — cannot verify thread ownership.
            # Fail closed: deny the request rather than skipping authorization.
            logger.error(
                "Checkpointer unavailable; denying access to existing thread",
                extra={"user_id": user_id, "thread_id": thread_id}
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Thread ownership verification unavailable; please retry.",
            )
        else:
            # Import here to avoid circular dependency
            from langgraph.checkpoint.base import CheckpointTuple
            from app.agents.graph import get_graph

            try:
                # Get the graph instance WITH the checkpointer to access state
                graph_instance = get_graph(checkpointer)

                # Get the current state to verify ownership
                existing_state = await graph_instance.aget_state(
                    config={"configurable": {
                        "thread_id": thread_id, "checkpoint_ns": ""}},
                    subgraphs=False
                )

                # Check if thread exists
                if not existing_state.values:
                    logger.warning(
                        "Thread not found",
                        extra={"user_id": user_id, "thread_id": thread_id}
                    )
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Thread not found"
                    )

                # Verify ownership
                state_user_id = existing_state.values.get("user_id")
                if state_user_id != user_id:
                    logger.warning(
                        "Access denied to thread",
                        extra={
                            "user_id": user_id,
                            "thread_id": thread_id,
                            "owner_id": state_user_id
                        }
                    )
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Thread not found"  # Don't reveal existence to unauthorized user
                    )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(
                    "Error verifying thread ownership - denying access",
                    extra={
                        "user_id": user_id,
                        "thread_id": thread_id,
                        "error": str(e),
                        "error_type": type(e).__name__
                    },
                    exc_info=True
                )
                # Fail closed: deny access if we can't verify ownership
                # This is more secure than allowing unverified access
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Unable to verify thread access"
                )

    # Note: No need to manually initialize thread state for new threads
    # The stream_agent() function automatically creates initial state with user_id
    # via create_initial_state(), which ensures RLS policies work correctly.
    # Manual initialization with aupdate_state() causes database connection issues
    # (pipeline mode conflicts) when streaming immediately after.

    # Unpack rate limit info for headers
    limit, remaining, reset_time = rate_limit_info

    try:
        if chat_request.stream:
            # === STREAMING MODE (SSE) ===
            logger.debug(
                "Starting SSE stream",
                extra={"user_id": user_id, "thread_id": str(thread_id)}
            )

            return StreamingResponse(
                sse_generator(
                    query=chat_request.message,
                    thread_id=thread_id,
                    user_id=user_id,
                    request=request,
                    is_new_thread=is_new_thread,
                    custom_title=chat_request.title,
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",  # Disable nginx buffering
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(reset_time),
                }
            )

        else:
            # === NON-STREAMING MODE (JSON) ===
            logger.debug(
                "Running non-streaming chat",
                extra={"user_id": user_id, "thread_id": str(thread_id)}
            )

            # Run agent and wait for completion
            result = await run_agent(
                query=chat_request.message,
                thread_id=thread_id,
                user_id=user_id,
            )

            logger.info(
                "Chat completed (non-streaming)",
                extra={
                    "user_id": user_id,
                    "thread_id": str(thread_id),
                    "response_length": len(result.content) if hasattr(result, 'content') else 0,
                }
            )

            # Return JSONResponse with rate limit headers
            from fastapi.responses import JSONResponse
            return JSONResponse(
                content=result.model_dump() if hasattr(result, 'model_dump') else result,
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(reset_time),
                }
            )

    except ValueError as e:
        # Validation errors
        logger.warning(
            "Chat request validation failed",
            extra={"user_id": user_id, "error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )

    except Exception as e:
        # Unexpected errors
        logger.error(
            "Chat request failed",
            extra={"user_id": user_id, "error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat request failed: {str(e)}"
        )
