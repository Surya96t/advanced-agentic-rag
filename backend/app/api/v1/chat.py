"""
Chat/query endpoint with SSE streaming.

This module provides the chat endpoint that integrates with the agentic RAG system
from Phase 4, supporting both streaming (SSE) and non-streaming responses.

Phase 5: Uses hardcoded user_id for testing without authentication
Phase 6: Will add JWT authentication
"""

import json
from typing import AsyncIterator
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.agents.graph import run_agent, stream_agent
from app.api.deps import UserID
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.events import SSEEventType
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


# ============================================================================
# SSE Helper Functions
# ============================================================================


async def sse_generator(
    query: str,
    thread_id: UUID | None,
    user_id: str,
) -> AsyncIterator[str]:
    """
    Generate Server-Sent Events (SSE) from the agent stream.

    SSE format:
        event: <event_type>
        data: <json_data>

        (blank line separator)

    Args:
        query: User's question
        thread_id: Thread ID for conversation
        user_id: User identifier

    Yields:
        Formatted SSE strings
    """
    try:
        async for event in stream_agent(query, thread_id, user_id):
            # Event structure: {"event": "event_type", "data": "json_string"}
            event_type = event.get("event", "unknown")
            event_data = event.get("data", "{}")

            # Format as SSE
            sse_message = f"event: {event_type}\ndata: {event_data}\n\n"
            yield sse_message

    except Exception as e:
        logger.error(
            "Error in SSE stream",
            extra={"error": str(e), "user_id": user_id},
            exc_info=True
        )
        # Send error event
        error_event = {
            "event": SSEEventType.AGENT_ERROR,
            "data": json.dumps({
                "error": str(e),
                "message": "Stream encountered an error"
            })
        }
        yield f"event: {error_event['event']}\ndata: {error_event['data']}\n\n"

        # Send end event
        end_event = {
            "event": SSEEventType.END,
            "data": json.dumps({"done": True, "error": True})
        }
        yield f"event: {end_event['event']}\ndata: {end_event['data']}\n\n"


# ============================================================================
# Endpoints
# ============================================================================


@router.post(
    "",
    summary="Chat with the agentic RAG system",
    description="Send a message and get an AI-generated response using agentic retrieval-augmented generation",
)
async def chat(
    request: ChatRequest,
    user_id: UserID,
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
            "message_preview": request.message[:100],
            "stream": request.stream,
            "thread_id": str(request.thread_id) if request.thread_id else "new",
        }
    )

    # Generate thread_id if not provided
    thread_id = request.thread_id or uuid4()

    try:
        if request.stream:
            # === STREAMING MODE (SSE) ===
            logger.debug(
                "Starting SSE stream",
                extra={"user_id": user_id, "thread_id": str(thread_id)}
            )

            return StreamingResponse(
                sse_generator(
                    query=request.message,
                    thread_id=thread_id,
                    user_id=user_id,
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",  # Disable nginx buffering
                }
            )

        else:
            # === NON-STREAMING MODE (JSON) ===
            logger.debug(
                "Running non-streaming chat",
                extra={"user_id": user_id, "thread_id": str(thread_id)}
            )

            # Run agent and wait for completion
            response = await run_agent(
                query=request.message,
                thread_id=thread_id,
                user_id=user_id,
            )

            logger.info(
                "Chat completed (non-streaming)",
                extra={
                    "user_id": user_id,
                    "thread_id": str(thread_id),
                    "response_length": len(response.content) if hasattr(response, 'content') else 0,
                }
            )

            return response

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
