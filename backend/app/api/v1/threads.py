"""
Thread management endpoints.

Provides CRUD operations for chat threads stored in the LangGraph checkpointer.
Allows users to list, view, create, and delete conversation threads.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.api.deps import UserID
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/threads", tags=["threads"])


# ============================================================================
# Schemas
# ============================================================================


class ThreadMetadata(BaseModel):
    """Metadata for a chat thread."""

    thread_id: str = Field(..., description="Unique thread identifier")
    title: str = Field(...,
                       description="Thread title (first message or custom)")
    preview: str | None = Field(
        None, description="Preview of last message (first 100 chars)")
    message_count: int = Field(..., ge=0,
                               description="Number of messages in thread")
    created_at: datetime = Field(..., description="Thread creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    user_id: str = Field(..., description="Owner user ID")


class ThreadDetail(BaseModel):
    """Detailed thread information with full message history."""

    metadata: ThreadMetadata
    messages: list[dict[str, Any]] = Field(
        ..., description="Full conversation history")


class CreateThreadRequest(BaseModel):
    """Request to create a new thread."""

    title: str | None = Field(
        None, description="Optional custom title (generated from first message if not provided)")


class CreateThreadResponse(BaseModel):
    """Response after creating a new thread."""

    thread_id: str = Field(..., description="ID of the newly created thread")
    title: str = Field(..., description="Thread title")


class UpdateThreadRequest(BaseModel):
    """Request to update thread metadata."""

    title: str = Field(..., description="New thread title")


class DeleteThreadResponse(BaseModel):
    """Response after deleting a thread."""

    success: bool = Field(..., description="Whether deletion was successful")
    thread_id: str = Field(..., description="ID of the deleted thread")


# ============================================================================
# Helper Functions
# ============================================================================


async def get_thread_metadata_from_checkpoint(
    thread_id: str,
    checkpointer,
    user_id: str,
) -> ThreadMetadata | None:
    """
    Extract thread metadata from the latest checkpoint.

    Args:
        thread_id: Thread identifier
        checkpointer: LangGraph checkpointer instance
        user_id: User ID for ownership verification

    Returns:
        ThreadMetadata if found and owned by user, None otherwise
    """
    try:
        logger.debug(f"Fetching checkpoint for thread {thread_id}")

        # Query checkpointer for latest checkpoint
        # This uses the LangGraph checkpointer's get method
        config = {"configurable": {"thread_id": thread_id}}
        checkpoint = await checkpointer.aget(config)

        if not checkpoint:
            logger.debug(f"No checkpoint found for thread {thread_id}")
            return None

        logger.debug(f"Checkpoint keys: {checkpoint.keys()}")

        # Extract state from checkpoint
        state = checkpoint.get("channel_values", {})
        logger.debug(f"State keys: {state.keys() if state else 'None'}")

        messages = state.get("messages", [])
        logger.info(f"Thread {thread_id} has {len(messages)} messages")

        # Verify ownership
        state_user_id = state.get("user_id")
        if state_user_id != user_id:
            logger.warning(
                f"Thread {thread_id} access denied for user {user_id} (owner: {state_user_id})"
            )
            return None

        # Extract metadata - query database directly for fresh metadata
        # This ensures we get the latest custom_title that was just updated
        # Use a dedicated connection to avoid concurrency/pipeline issues
        from psycopg import AsyncConnection
        from app.core.config import settings
        
        async with await AsyncConnection.connect(settings.supabase_connection_string) as conn:
            async with conn.cursor() as cur:
                # Fetch metadata from latest checkpoint AND persistent title from any checkpoint
                await cur.execute(
                    """
                    SELECT 
                        (SELECT metadata FROM checkpoints WHERE thread_id = %s ORDER BY checkpoint_id DESC LIMIT 1) as latest_metadata,
                        (SELECT metadata->>'custom_title' FROM checkpoints WHERE thread_id = %s AND metadata->>'custom_title' IS NOT NULL ORDER BY checkpoint_id DESC LIMIT 1) as persistent_title
                    """,
                    (thread_id, thread_id)
                )
                result = await cur.fetchone()
                
                persistent_title = None
                if result:
                    # Unpack result
                    metadata_raw, persistent_title = result
                    
                    if metadata_raw is None:
                        checkpoint_metadata = {}
                    elif isinstance(metadata_raw, str):
                        # Parse JSON string to dict
                        import json
                        try:
                            logger.warning(f"Bad metadata json for thread {thread_id}")
                        except json.JSONDecodeError:
                            logger.error(
                                f"Failed to parse metadata JSON for thread {thread_id}")
                            checkpoint_metadata = {}
                    elif isinstance(metadata_raw, dict):
                        checkpoint_metadata = metadata_raw
                    else:
                        logger.warning(
                            f"Unexpected metadata type for thread {thread_id}: {type(metadata_raw)}")
                        checkpoint_metadata = {}
                else:
                    checkpoint_metadata = {}

        # Extract message info
        first_message = next(
            (msg for msg in messages if hasattr(
                msg, "type") and msg.type == "human"),
            None
        )
        last_message = messages[-1] if messages else None

        # Get title - prefer persistent_title from ANY checkpoint, fallback to current metadata
        custom_title = persistent_title
        if not custom_title:
            custom_title = checkpoint_metadata.get("custom_title")

        if custom_title:
            title = custom_title
            logger.debug(f"Using custom title: {title}")
        elif first_message:
            title = first_message.content[:50] + \
                "..." if len(
                    first_message.content) > 50 else first_message.content
            logger.debug(f"Generated title from first message: {title}")
        else:
            title = "New Chat"
            logger.debug("Using default title: New Chat")

        # Safely extract preview from last message
        # Check if message has content attribute and it's a string before slicing
        preview = None
        if last_message:
            content = getattr(last_message, "content", None)
            if content and isinstance(content, str):
                preview = content[:100]

        # Get timestamps from checkpoint metadata
        _now_iso = datetime.now(timezone.utc).isoformat()
        created_at = checkpoint_metadata.get("created_at", _now_iso)
        updated_at = checkpoint_metadata.get("updated_at", _now_iso)

        return ThreadMetadata(
            thread_id=thread_id,
            title=title,
            preview=preview,
            message_count=len(messages),
            created_at=datetime.fromisoformat(
                created_at.replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(
                updated_at.replace("Z", "+00:00")),
            user_id=user_id,
        )

    except Exception as e:
        logger.error(
            "Error extracting thread metadata - unable to verify ownership",
            extra={
                "thread_id": thread_id,
                "user_id": user_id,
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        # Re-raise to force fail-closed behavior
        # Callers will handle this by denying access
        raise


async def list_user_threads_from_db(
    user_id: str,
    checkpointer,
) -> list[ThreadMetadata]:
    """
    List all threads for a user by querying the checkpointer database.

    This queries the PostgreSQL checkpoints table directly for efficiency.
    It creates a dedicated connection to avoid concurrency issues with the
    shared checkpointer connection.

    Args:
        user_id: User identifier
        checkpointer: LangGraph checkpointer instance (used only for type/config reference if needed, currently unused for connection)

    Returns:
        List of ThreadMetadata objects, sorted by updated_at descending
    """
    try:
        # Create a dedicated connection for this read operation
        # This prevents "NoneType object has no attribute '_fetch_gen'" errors
        # caused by sharing the checkpointer's single connection across concurrent requests
        from psycopg import AsyncConnection
        from app.core.config import settings
        
        # Determine connection string (fallback to checkpointer's if available, else settings)
        conn_string = settings.supabase_connection_string

        # Query for all unique thread_ids with their latest checkpoints, 
        # but also fetch the custom_title from ANY checkpoint in the thread
        # (since new checkpoints created by LangGraph might miss the metadata update)
        query = """
        WITH user_checkpoints AS (
            SELECT 
                thread_id,
                checkpoint,
                metadata,
                checkpoint_id
            FROM checkpoints
            WHERE checkpoint_ns = ''
              AND checkpoint->'channel_values'->>'user_id' = %s
              AND (
                checkpoint->'channel_values'->>'query' IS NOT NULL 
                OR checkpoint->'channel_values'->>'generated_response' IS NOT NULL
              )
        ),
        latest_checkpoints AS (
            SELECT DISTINCT ON (thread_id)
                thread_id,
                checkpoint,
                metadata,
                checkpoint_id
            FROM user_checkpoints
            ORDER BY thread_id, checkpoint_id DESC
        ),
        thread_titles AS (
            SELECT DISTINCT ON (thread_id)
                thread_id,
                metadata->>'custom_title' as persistent_title
            FROM checkpoints
            WHERE checkpoint_ns = ''
              AND metadata->>'custom_title' IS NOT NULL
            ORDER BY thread_id, checkpoint_id DESC
        )
        SELECT
            lc.thread_id,
            lc.checkpoint,
            lc.metadata,
            lc.checkpoint_id,
            tt.persistent_title
        FROM latest_checkpoints lc
        LEFT JOIN thread_titles tt ON lc.thread_id = tt.thread_id
        ORDER BY lc.checkpoint_id DESC
        """

        # Import dict_row for dictionary-style results
        from psycopg.rows import dict_row

        # autocommit=True: this is a pure SELECT — no transaction needed.
        # Eliminates the COMMIT call in __aexit__ which crashes when Supavisor
        # drops an idle connection mid-request.
        # connect_timeout: fail fast (10s) instead of hanging indefinitely.
        # statement_timeout: kill the query if Postgres stalls beyond 30s.
        async with await AsyncConnection.connect(
            conn_string,
            autocommit=True,
            connect_timeout=10,
            options="-c statement_timeout=30000",
        ) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(query, (user_id,))
                rows = await cur.fetchall()

        logger.info(f"Query returned {len(rows)} rows")

        threads = []
        for row in rows:
            try:
                thread_id = row['thread_id']
                
                # Parse checkpoint directly without re-querying
                # This is much faster and avoids connection issues
                checkpoint = row['checkpoint']
                metadata_raw = row['metadata']
                
                # 1. Parse Metadata
                checkpoint_metadata = {}
                if metadata_raw:
                    if isinstance(metadata_raw, dict):
                        checkpoint_metadata = metadata_raw
                    elif isinstance(metadata_raw, str):
                        try:
                            import json
                            checkpoint_metadata = json.loads(metadata_raw)
                        except json.JSONDecodeError:
                            logger.warn(f"Bad metadata json for thread {thread_id}")
                
                # 2. Parse State/Messages
                state = checkpoint.get("channel_values", {})
                messages = state.get("messages", [])
                
                # 3. Extract Details (Title, Preview, Counts)
                first_message = next(
                    (msg for msg in messages if hasattr(msg, "type") and msg.type == "human"), 
                    None
                )
                last_message = messages[-1] if messages else None
                
                # Title logic
                # Prefer persistent title from ANY checkpoint first (query result)
                # Then fallback to metadata from the LATEST checkpoint
                custom_title = row.get("persistent_title")
                if not custom_title:
                    custom_title = checkpoint_metadata.get("custom_title")
                
                if custom_title:
                    title = custom_title
                elif first_message:
                    # Handle LangChain message object or dict
                    content = getattr(first_message, "content", "") if hasattr(first_message, "content") else str(first_message)
                    title = content[:50] + "..." if len(content) > 50 else content
                else:
                    title = "New Chat"
                
                # Preview logic
                preview = None
                if last_message:
                    content = getattr(last_message, "content", None)
                    if content and isinstance(content, str):
                        preview = content[:100]

                # Timestamps
                _now_iso = datetime.now(timezone.utc).isoformat()
                created_at = checkpoint_metadata.get("created_at", _now_iso)
                updated_at = checkpoint_metadata.get("updated_at", _now_iso)

                threads.append(ThreadMetadata(
                    thread_id=thread_id,
                    title=title,
                    preview=preview,
                    message_count=len(messages),
                    created_at=datetime.fromisoformat(created_at.replace("Z", "+00:00")),
                    updated_at=datetime.fromisoformat(updated_at.replace("Z", "+00:00")),
                    user_id=user_id,
                ))
            except Exception as e:
                logger.error(f"Error processing thread row {row.get('thread_id')}: {e}")
                continue

        logger.info(f"Found {len(threads)} threads for user {user_id}")
        return threads

    except Exception as e:
        logger.error(
            f"Error listing threads from database: {e}", exc_info=True)
        raise


# ============================================================================
# Endpoints
# ============================================================================


@router.get(
    "",
    response_model=list[ThreadMetadata],
    summary="List all chat threads",
    description="Get a list of all chat threads for the current user",
)
async def list_threads(
    user_id: UserID,
    request: Request,
) -> list[ThreadMetadata]:
    """
    List all chat threads for the current user.

    Returns threads sorted by most recently updated first.

    Args:
        user_id: Current user ID (injected via dependency)
        request: FastAPI request (to access checkpointer from app.state)

    Returns:
        List of ThreadMetadata objects

    Raises:
        HTTPException: 500 if database query fails
    """
    logger.info(f"Listing threads for user {user_id}")

    try:
        checkpointer = request.app.state.checkpointer
        threads = await list_user_threads_from_db(user_id, checkpointer)

        logger.info(f"Found {len(threads)} threads for user {user_id}")
        return threads

    except Exception as e:
        logger.error(f"Failed to list threads: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve threads"
        )


@router.get(
    "/{thread_id}",
    response_model=ThreadDetail,
    summary="Get thread details",
    description="Get detailed information about a specific thread including full message history",
)
async def get_thread(
    thread_id: str,
    user_id: UserID,
    request: Request,
) -> ThreadDetail:
    """
    Get detailed information about a specific thread.

    Includes full conversation history with all messages.

    Args:
        thread_id: Thread identifier
        user_id: Current user ID (injected via dependency)
        request: FastAPI request (to access checkpointer from app.state)

    Returns:
        ThreadDetail with metadata and messages

    Raises:
        HTTPException: 404 if thread not found or not owned by user
        HTTPException: 500 if database query fails
    """
    logger.info(f"Getting thread {thread_id} for user {user_id}")

    try:
        checkpointer = request.app.state.checkpointer

        # Get metadata first (includes ownership check)
        metadata = await get_thread_metadata_from_checkpoint(
            thread_id, checkpointer, user_id
        )

        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found or access denied"
            )

        # Get full checkpoint to extract messages
        config = {"configurable": {"thread_id": thread_id}}
        checkpoint = await checkpointer.aget(config)

        if not checkpoint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread checkpoint not found"
            )

        # Extract messages
        state = checkpoint.get("channel_values", {})
        messages_raw = state.get("messages", [])

        # Convert LangChain messages to dict format
        messages = []
        for msg in messages_raw:
            if hasattr(msg, "type") and hasattr(msg, "content"):
                # Map LangChain message types to API role types
                msg_type = msg.type
                if msg_type == "human":
                    role = "user"
                elif msg_type == "ai":
                    role = "assistant"
                elif msg_type == "system":
                    role = "system"
                elif msg_type == "tool":
                    role = "tool"
                elif msg_type in ("function", "function_call"):
                    role = "function"
                else:
                    # Preserve unknown types for debugging
                    role = msg_type
                    logger.warning(
                        f"Unknown message type '{msg_type}' in thread {thread_id}")

                # Extract citations from additional_kwargs OR response_metadata
                citations = []
                additional_kwargs = getattr(msg, "additional_kwargs", {})
                response_metadata = getattr(msg, "response_metadata", {})
                
                # Check both locations for citations
                raw_citations = []
                if additional_kwargs and "citations" in additional_kwargs:
                    raw_citations = additional_kwargs["citations"]
                elif response_metadata and "citations" in response_metadata:
                    raw_citations = response_metadata["citations"]
                
                if raw_citations:
                    # Map stored citation structure to API citation structure
                    for c in raw_citations:
                        citations.append({
                            "chunk_id": c.get("chunk_id", ""),
                            "document_title": c.get("document_title", "Unknown"),
                            "content": c.get("content", ""),
                            # Map generator's 'score' (RRF) to similarity_score
                            "similarity_score": c.get("score", 0.0),
                            "original_score": c.get("original_score"),
                            "document_id": c.get("document_id", "unknown"),
                            "chunk_index": c.get("index"),
                        })

                # Extract citation_map (marker → source metadata) for inline citations
                citation_map = None
                raw_citation_map = additional_kwargs.get("citation_map") if additional_kwargs else None
                if raw_citation_map:
                    citation_map = {
                        str(k): {
                            "chunk_id": str(v.get("chunk_id", "")),
                            "document_id": str(v.get("document_id", "")),
                            "document_title": v.get("document_title", ""),
                            "content": v.get("content", ""),
                            "score": v.get("score"),
                            "source": v.get("source"),
                        }
                        for k, v in raw_citation_map.items()
                    }

                messages.append({
                    "role": role,
                    "content": msg.content,
                    "timestamp": getattr(msg, "timestamp", None),
                    "citations": citations,
                    "citation_map": citation_map,
                })

        return ThreadDetail(
            metadata=metadata,
            messages=messages,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get thread details: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve thread details"
        )


@router.post(
    "",
    response_model=CreateThreadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new thread",
    description="Create a new chat thread (returns thread_id to use for subsequent messages)",
)
async def create_thread(
    thread_request: CreateThreadRequest,
    user_id: UserID,
    request: Request,
) -> CreateThreadResponse:
    """
    Create a new chat thread by initializing its state.

    Creates a new thread with initial empty state persisted to the database.
    This allows the thread to appear in the user's thread list immediately.

    The thread is created by using update_state() to initialize the state
    without executing any graph nodes, which:
    1. Initializes the state with user_id for ownership
    2. Persists the checkpoint via LangGraph's update_state
    3. Returns a thread_id that can be used for subsequent messages

    Args:
        thread_request: Optional thread creation parameters
        user_id: Current user ID (injected via dependency)
        request: FastAPI request (to access checkpointer from app.state)

    Returns:
        CreateThreadResponse with thread_id and title

    Raises:
        HTTPException: 500 if thread creation fails
    """
    logger.info(f"Creating new thread for user {user_id}")

    try:
        thread_id = str(uuid4())
        title = thread_request.title or "New Chat"

        # Get checkpointer from app state
        checkpointer = request.app.state.checkpointer

        # Create initial empty state for the thread
        from app.agents.graph import create_initial_state, get_graph

        # Don't create a HumanMessage for empty thread initialization
        # Just set up the state structure with user_id
        initial_state = {
            "original_query": "",
            "query": "",
            "user_id": user_id,
            "messages": [],  # Empty - will be populated when first message is sent
            "expanded_queries": [],
            "retrieved_chunks": [],
            "retry_count": 0,
            "sources": [],
            "query_type": "complex_standalone",
            "needs_retrieval": True,
            "conversation_summary": "",
            "context_window_tokens": 0,
            "pipeline_path": "complex",
            "metadata": {
                "start_time": None,
                "end_time": None,
                "nodes_executed": [],
                "total_tokens": 0,
                "total_cost": 0.0,
            },
            "feedback_requested": False,
        }

        # Configuration for LangGraph execution
        config = {
            "configurable": {
                "thread_id": thread_id,
                "user_id": user_id,
            }
        }

        # Get compiled graph with checkpointer
        graph_instance = get_graph(checkpointer=checkpointer)

        # Use update_state to initialize the thread without executing nodes
        # This is more efficient than ainvoke() since it doesn't run the graph
        logger.debug(f"Initializing thread {thread_id} with update_state")
        await graph_instance.aupdate_state(
            config,
            initial_state,
            as_node="__start__",  # Initialize as the start node
        )

        # Persist custom title to checkpoint metadata if provided
        # This ensures get_thread_metadata_from_checkpoint can retrieve it
        if thread_request.title:
            from psycopg import AsyncConnection
            from app.core.config import settings
            conn_string = settings.supabase_connection_string
            
            async with await AsyncConnection.connect(
                conn_string,
                autocommit=True,
                connect_timeout=10,
                options="-c statement_timeout=30000",
            ) as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        UPDATE checkpoints
                        SET metadata = jsonb_set(
                            COALESCE(metadata, '{}'::jsonb),
                            '{custom_title}',
                            to_jsonb(%s::text)
                        )
                        WHERE thread_id = %s
                        """,
                        (title, thread_id)
                    )
                    await conn.commit()
            logger.debug(
                f"Saved custom title '{title}' to checkpoint metadata")

        logger.info(
            f"Created and persisted thread {thread_id} with title '{title}'")

        return CreateThreadResponse(
            thread_id=thread_id,
            title=title,
        )

    except Exception as e:
        logger.error(f"Failed to create thread: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create thread"
        )


@router.delete(
    "/{thread_id}",
    response_model=DeleteThreadResponse,
    summary="Delete a thread",
    description="Permanently delete a chat thread and all its messages",
)
async def delete_thread(
    thread_id: str,
    user_id: UserID,
    request: Request,
) -> DeleteThreadResponse:
    """
    Delete a chat thread permanently.

    Removes all checkpoints associated with the thread from the database.
    This action cannot be undone.

    Args:
        thread_id: Thread identifier to delete
        user_id: Current user ID (injected via dependency)
        request: FastAPI request (to access checkpointer from app.state)

    Returns:
        DeleteThreadResponse with success status

    Raises:
        HTTPException: 404 if thread not found or not owned by user
        HTTPException: 500 if deletion fails
    """
    logger.info(f"Deleting thread {thread_id} for user {user_id}")

    try:
        checkpointer = request.app.state.checkpointer

        # Verify ownership first
        try:
            metadata = await get_thread_metadata_from_checkpoint(
                thread_id, checkpointer, user_id
            )
        except Exception as e:
            # Fail closed: deny access if we can't verify ownership
            logger.error(
                "Failed to verify thread ownership for deletion - denying access",
                extra={
                    "user_id": user_id,
                    "thread_id": thread_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                },
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unable to verify thread access"
            )

        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found or access denied"
            )

        # Delete all checkpoints for this thread
        conn = checkpointer.conn
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM checkpoints WHERE thread_id = %s",
                (thread_id,)
            )
            await conn.commit()

        logger.info(f"Successfully deleted thread {thread_id}")

        return DeleteThreadResponse(
            success=True,
            thread_id=thread_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete thread: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete thread"
        )


@router.patch(
    "/{thread_id}",
    response_model=ThreadMetadata,
    summary="Update thread metadata",
    description="Update thread properties like title",
)
async def update_thread(
    thread_id: str,
    update_request: UpdateThreadRequest,
    user_id: UserID,
    request: Request,
) -> ThreadMetadata:
    """
    Update thread metadata (currently only title).

    Args:
        thread_id: Thread identifier
        update_request: Update parameters
        user_id: Current user ID (injected via dependency)
        request: FastAPI request (to access checkpointer from app.state)

    Returns:
        Updated ThreadMetadata

    Raises:
        HTTPException: 404 if thread not found or not owned by user
        HTTPException: 500 if update fails

    Note:
        Title updates are stored in the checkpoint metadata for persistence.
    """
    logger.info(f"Updating thread {thread_id} for user {user_id}")

    try:
        checkpointer = request.app.state.checkpointer

        # Verify ownership first
        try:
            metadata = await get_thread_metadata_from_checkpoint(
                thread_id, checkpointer, user_id
            )
        except Exception as e:
            # Fail closed: deny access if we can't verify ownership
            logger.error(
                "Failed to verify thread ownership for update - denying access",
                extra={
                    "user_id": user_id,
                    "thread_id": thread_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                },
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unable to verify thread access"
            )

        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found or access denied"
            )

        # Update metadata in ALL checkpoints for this thread
        # This ensures the title persists across all checkpoint retrievals
        # Use a dedicated connection to avoid concurrency/pipeline issues
        from psycopg import AsyncConnection
        from app.core.config import settings
        conn_string = settings.supabase_connection_string

        async with await AsyncConnection.connect(
            conn_string,
            autocommit=True,
            connect_timeout=10,
            options="-c statement_timeout=30000",
        ) as conn:
            async with conn.cursor() as cur:
                # Update the metadata JSONB column for ALL checkpoints in this thread
                # We store custom_title in metadata to preserve it across checkpoints
                await cur.execute(
                    """
                    UPDATE checkpoints
                    SET metadata = jsonb_set(
                        COALESCE(metadata, '{}'::jsonb),
                        '{custom_title}',
                        to_jsonb(%s::text)
                    )
                    WHERE thread_id = %s
                    """,
                    (update_request.title, thread_id)
                )
                await conn.commit()

        # Return updated metadata
        metadata.title = update_request.title
        logger.info(f"Successfully updated thread {thread_id}")

        return metadata

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update thread: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update thread"
        )
