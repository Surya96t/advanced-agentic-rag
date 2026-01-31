"""
LangGraph StateGraph definition and compilation.

This module assembles the complete agentic RAG workflow graph with:
- 5 agent nodes (router, query_expander, retriever, generator, validator)
- Cyclic validation loop with retry logic
- PostgreSQL checkpointing for persistence
- LangSmith tracing for observability
- Multi-mode streaming support
"""

from app.utils.logger import get_logger
from app.schemas.events import (
    SSEEventType,
    AgentStartEvent,
    AgentCompleteEvent,
    AgentErrorEvent,
    ProgressEvent,
    TokenEvent,
    CitationEvent,
    ValidationEvent,
    EndEvent,
)
from app.schemas.chat import ChatResponse
from app.core.config import settings
from app.agents.nodes import (
    router_node,
    query_expander_node,
    retriever_node,
    generator_node,
    validator_node,
)
from app.agents.state import AgentState, create_initial_state
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from uuid import UUID, uuid4
from typing import AsyncIterator
import os

# CRITICAL: Set BEFORE any PostgreSQL connections are created
# Supabase Transaction Pooler requires prepared statements to be disabled
os.environ["PGPREPARE_THRESHOLD"] = "0"


logger = get_logger(__name__)

# ============================================================================
# Graph Construction
# ============================================================================


def build_graph() -> StateGraph:
    """
    Build the complete LangGraph StateGraph for agentic RAG.

    Graph Flow:
    1. START → router
    2. router → (COMMAND decides) → retriever (simple) OR query_expander (complex/ambiguous)
    3. query_expander → retriever
    4. retriever → generator
    5. generator → validator
    6. validator → (COMMAND decides) → END (pass) OR query_expander (retry)

    Returns:
        Compiled StateGraph with checkpointing and tracing enabled
    """
    logger.info("Building LangGraph StateGraph for agentic RAG")

    # Create graph builder
    builder = StateGraph(AgentState)

    # Add all nodes
    logger.debug("Adding nodes to graph")
    builder.add_node("router", router_node)
    builder.add_node("query_expander", query_expander_node)
    builder.add_node("retriever", retriever_node)
    builder.add_node("generator", generator_node)
    builder.add_node("validator", validator_node)

    # Add edges
    logger.debug("Adding edges to graph")

    # Entry point
    builder.add_edge(START, "router")

    # Router uses Command pattern to decide routing
    # (No explicit conditional edge needed, Command handles it)

    # Linear flow after expansion
    builder.add_edge("query_expander", "retriever")
    builder.add_edge("retriever", "generator")
    builder.add_edge("generator", "validator")

    # Validator uses Command pattern to decide:
    # - goto="__end__" if validation passes
    # - goto="query_expander" if retry needed
    # (No explicit conditional edge needed, Command handles it)

    logger.info("Graph construction complete")
    return builder


async def get_checkpointer():
    """
    Create PostgreSQL checkpointer for persistent agent state.

    Uses Supabase connection string from settings.
    Enables pause/resume functionality for long-running workflows.

    Returns:
        AsyncPostgresSaver instance configured with database connection

    Raises:
        Exception: If database connection fails

    Note:
        Import is done lazily to avoid blocking Studio graph loading.
        This returns the context manager itself, which must be used with
        `async with` by the caller.
    """
    # Lazy import to avoid module-level import issues with Studio
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    logger.info("Initializing PostgreSQL checkpointer")

    try:
        # For Supabase Transaction Pooler, prepared statements are disabled
        # via the PGPREPARE_THRESHOLD=0 environment variable set at module top.
        # Do NOT append prepare_threshold to the connection string -
        # it's not a valid psycopg3 URI parameter and will cause errors.
        conn_string = settings.supabase_connection_string

        logger.debug(
            f"Using PGPREPARE_THRESHOLD=0 from environment for Supabase compatibility")

        # from_conn_string returns an async context manager
        checkpointer = AsyncPostgresSaver.from_conn_string(
            conn_string=conn_string
        )

        logger.info("Checkpointer context manager created successfully")
        return checkpointer

    except Exception as e:
        logger.error(f"Failed to initialize checkpointer: {e}")
        raise


# ============================================================================
# Graph Compilation
# ============================================================================

# Module-level graph for LangGraph Studio (no checkpointing)
# This allows Studio to visualize the graph structure
logger.info("Compiling graph for LangGraph Studio (no checkpointing)")
_builder = build_graph()
graph = _builder.compile()
logger.info(
    "✅ Studio graph compiled (use get_graph() for production with checkpointing)")

# Cache for runtime graph with checkpointer
_compiled_graph = None
_checkpointer_cm = None


async def get_graph():
    """
    Get or create the compiled LangGraph with checkpointer for production use.

    This function defers checkpointer initialization to runtime to properly wire in
    the async PostgreSQL checkpointer. The compiled graph is cached after
    first initialization.

    Returns:
        Compiled StateGraph with checkpointing enabled

    Raises:
        Exception: If checkpointer initialization or graph compilation fails

    Note:
        - For LangGraph Studio: use the module-level `graph` variable
        - For production runtime: use this `get_graph()` function

        The checkpointer uses an async context manager that stays open for 
        the lifetime of the application.
    """
    global _compiled_graph, _checkpointer_cm

    # Return cached graph if already compiled
    if _compiled_graph is not None:
        return _compiled_graph

    logger.info(
        "Compiling LangGraph with checkpointing (first-time production initialization)")

    try:
        # Get checkpointer context manager
        _checkpointer_cm = await get_checkpointer()

        # Enter the context manager to get the actual checkpointer instance
        checkpointer_instance = await _checkpointer_cm.__aenter__()

        # Build and compile graph with checkpointer
        builder = build_graph()
        _compiled_graph = builder.compile(checkpointer=checkpointer_instance)

        logger.info(
            "✅ LangGraph compiled successfully with checkpointing enabled")
        return _compiled_graph

    except Exception as e:
        logger.error(f"Failed to compile graph with checkpointer: {e}")
        # Clean up if context manager was entered
        if _checkpointer_cm is not None:
            try:
                await _checkpointer_cm.__aexit__(None, None, None)
            except Exception:
                pass
        raise


# ============================================================================
# Helper Functions
# ============================================================================


def validate_thread_id(thread_id: str | UUID | None) -> UUID:
    """
    Validate and convert thread_id to UUID.

    Args:
        thread_id: Thread ID as string, UUID, or None

    Returns:
        Valid UUID instance

    Raises:
        ValueError: If thread_id string is not a valid UUID format

    Example:
        >>> validate_thread_id("123e4567-e89b-12d3-a456-426614174000")
        UUID('123e4567-e89b-12d3-a456-426614174000')
        >>> validate_thread_id(None)
        UUID('newly-generated-uuid')
        >>> validate_thread_id("invalid")
        ValueError: Invalid thread_id format: 'invalid'. Must be a valid UUID.
    """
    if thread_id is None:
        return uuid4()

    if isinstance(thread_id, UUID):
        return thread_id

    # Validate string is a valid UUID
    try:
        return UUID(str(thread_id))
    except (ValueError, AttributeError) as e:
        raise ValueError(
            f"Invalid thread_id format: '{thread_id}'. Must be a valid UUID string."
        ) from e


# ============================================================================
# Graph Execution Helpers
# ============================================================================


async def run_agent(
    query: str,
    thread_id: str | UUID | None = None,
    user_id: str = "anonymous",
) -> ChatResponse:
    """
    Run the agentic RAG workflow and return final response.

    This is a simple invoke call that blocks until completion.
    Use `stream_agent()` for real-time streaming.

    Args:
        query: User's question
        thread_id: Optional conversation thread ID for checkpointing
        user_id: User identifier for RLS in database

    Returns:
        ChatResponse with generated answer, sources, and metadata

    Example:
        >>> response = await run_agent("How do I integrate Clerk with Prisma?")
        >>> print(response.content)
        "To integrate Clerk with Prisma..."
    """
    # Validate and convert thread_id
    try:
        thread_id = validate_thread_id(thread_id)
    except ValueError as e:
        logger.error(f"Invalid thread_id provided: {e}")
        return ChatResponse(
            content=f"Invalid thread_id: {str(e)}",
            sources=[],
            metadata={"error": str(e)}
        )

    logger.info(f"Running agent workflow for query: {query[:100]}...")
    logger.debug(f"Thread ID: {thread_id}, User ID: {user_id}")

    # Create initial state
    initial_state = create_initial_state(query)

    # Configuration for LangGraph execution
    config = {
        "configurable": {
            "thread_id": str(thread_id),
            "user_id": user_id,
        }
    }

    try:
        # Get compiled graph with checkpointer
        graph = await get_graph()

        # Invoke graph (blocks until completion)
        final_state = await graph.ainvoke(initial_state, config=config)

        # Build response from final state
        response = ChatResponse(
            content=final_state.get(
                "generated_response", "No response generated."),
            sources=final_state.get("sources", []),
            metadata={
                "thread_id": str(thread_id),
                "query": query,
                "complexity": final_state.get("query_complexity", "unknown"),
                "validation": final_state.get("validation_result", {}),
                **final_state.get("metadata", {}),
            }
        )

        logger.info(
            f"Agent workflow complete (thread: {thread_id})",
            complexity=final_state.get("query_complexity"),
            chunks_retrieved=len(final_state.get("retrieved_chunks", [])),
            retry_count=final_state.get("retry_count", 0),
        )

        return response

    except Exception as e:
        logger.error(f"Agent execution failed: {e}", exc_info=True)

        # Return error response
        return ChatResponse(
            content=f"I encountered an error: {str(e)}. Please try again.",
            sources=[],
            metadata={
                "thread_id": str(thread_id),
                "query": query,
                "error": str(e),
            }
        )


async def stream_agent(
    query: str,
    thread_id: str | UUID | None = None,
    user_id: str = "anonymous",
) -> AsyncIterator[dict]:
    """
    Stream agent execution with real-time SSE events.

    Emits events for:
    - Agent node starts/completions
    - Progress updates from nodes
    - LLM token streaming
    - Citation discoveries
    - Validation results
    - Final completion

    Args:
        query: User's question
        thread_id: Optional conversation thread ID
        user_id: User identifier for RLS

    Yields:
        SSE event dictionaries with "event" and "data" keys

    Example:
        >>> async for event in stream_agent("How does Clerk work?"):
        ...     print(f"{event['event']}: {event['data']}")
        agent_start: {"node": "router", ...}
        progress: {"message": "Analyzing query...", ...}
        agent_complete: {"node": "router", ...}
        ...
    """
    # Validate and convert thread_id
    try:
        thread_id = validate_thread_id(thread_id)
    except ValueError as e:
        logger.error(f"Invalid thread_id provided: {e}")
        # Yield error event for streaming
        yield {
            "event": SSEEventType.END.value,
            "data": EndEvent(
                thread_id="invalid",
                success=False,
                error=str(e),
            ).model_dump_json()
        }
        return

    logger.info(f"Streaming agent workflow for query: {query[:100]}...")
    logger.debug(f"Thread ID: {thread_id}, User ID: {user_id}")

    # Create initial state
    initial_state = create_initial_state(query)

    # Configuration
    config = {
        "configurable": {
            "thread_id": str(thread_id),
            "user_id": user_id,
        }
    }

    # Track previous node for event correlation
    current_node: str | None = None

    try:
        # Get compiled graph with checkpointer
        graph = await get_graph()

        # Stream with updates mode for node state changes
        async for event in graph.astream(
            initial_state,
            config=config,
            stream_mode="updates",  # Use single mode for simpler event handling
        ):
            # Event structure with single mode: {node_name: node_update}
            if not event:
                continue  # Skip empty events

            # Extract node name and update
            node_name = next(iter(event.keys()))
            node_update = event[node_name]

            # Emit agent_start if new node
            if node_name != current_node:
                if current_node:
                    # Complete previous node
                    yield {
                        "event": SSEEventType.AGENT_COMPLETE.value,
                        "data": AgentCompleteEvent(
                            agent=current_node,
                            result={},
                        ).model_dump_json()
                    }

                # Start new node
                current_node = node_name
                yield {
                    "event": SSEEventType.AGENT_START.value,
                    "data": AgentStartEvent(
                        agent=node_name,
                        message=f"Executing {node_name} node",
                    ).model_dump_json()
                }

            # Process specific update types
            # Citation events from retriever
            if node_name == "retriever" and "sources" in node_update:
                for source in node_update["sources"]:
                    # Safely extract required fields from source
                    chunk_id = source.get("chunk_id")
                    document_id = source.get("document_id")

                    # Skip sources missing required fields
                    if not chunk_id or not document_id:
                        logger.warning(
                            f"Skipping citation with missing required fields: "
                            f"chunk_id={chunk_id}, document_id={document_id}"
                        )
                        continue

                    # Emit citation event with safe field access
                    yield {
                        "event": SSEEventType.CITATION.value,
                        "data": CitationEvent(
                            chunk_id=chunk_id,
                            document_title=source.get(
                                "document_title", "Unknown Document"),
                            score=source.get("score", 0.0),
                            source=source.get("source", "unknown"),
                            preview=source.get("content", "")[
                                :200] if source.get("content") else None,
                        ).model_dump_json()
                    }

                # Validation events
                if node_name == "validator" and "validation_result" in node_update:
                    validation = node_update["validation_result"]
                    yield {
                        "event": SSEEventType.VALIDATION.value,
                        "data": ValidationEvent(
                            passed=validation.get("passed", False),
                            score=validation.get("score", 0.0),
                            issues=validation.get("issues", []),
                        ).model_dump_json()
                    }

        # Complete final node
        if current_node:
            yield {
                "event": SSEEventType.AGENT_COMPLETE.value,
                "data": AgentCompleteEvent(
                    agent=current_node,
                    result={},
                ).model_dump_json()
            }

        # Get final state to retrieve generated response
        final_state = await graph.aget_state(config)
        if final_state and final_state.values:
            generated_response = final_state.values.get(
                "generated_response", "")

            # Send complete response as a single token to preserve formatting
            if generated_response:
                yield {
                    "event": SSEEventType.TOKEN.value,
                    "data": TokenEvent(token=generated_response).model_dump_json()
                }

        # Final end event
        yield {
            "event": SSEEventType.END.value,
            "data": EndEvent(
                thread_id=str(thread_id),
                success=True,
            ).model_dump_json()
        }

        logger.info(f"Streaming complete for thread {thread_id}")

    except Exception as e:
        logger.error(f"Streaming failed: {e}", exc_info=True)

        # Emit error event
        if current_node:
            yield {
                "event": SSEEventType.AGENT_ERROR.value,
                "data": AgentErrorEvent(
                    agent=current_node,
                    error=str(e),
                ).model_dump_json()
            }

        yield {
            "event": SSEEventType.END.value,
            "data": EndEvent(
                thread_id=str(thread_id),
                success=False,
                error=str(e),
            ).model_dump_json()
        }


async def get_checkpoint(thread_id: str | UUID) -> dict | None:
    """
    Get the latest checkpoint for a conversation thread.

    Useful for debugging or displaying conversation history.

    Args:
        thread_id: Thread identifier

    Returns:
        Checkpoint state dict, or None if no checkpoint found

    Example:
        >>> checkpoint = await get_checkpoint("thread_123")
        >>> checkpoint["state"]["retry_count"]
        1
    """
    # Validate thread_id
    try:
        thread_id_uuid = validate_thread_id(thread_id)
        thread_id_str = str(thread_id_uuid)
    except ValueError as e:
        logger.error(f"Invalid thread_id provided: {e}")
        return None

    logger.info(f"Fetching checkpoint for thread {thread_id_str}")

    try:
        # Get compiled graph with checkpointer
        graph = await get_graph()

        # Get checkpoint from graph
        config = {"configurable": {"thread_id": thread_id_str}}
        state_snapshot = await graph.aget_state(config)

        if state_snapshot:
            logger.info(f"Checkpoint found for thread {thread_id_str}")
            return state_snapshot.values
        else:
            logger.info(f"No checkpoint found for thread {thread_id_str}")
            return None

    except Exception as e:
        logger.error(f"Failed to fetch checkpoint: {e}")
        return None


async def resume_agent(
    thread_id: str | UUID,
    user_id: str = "anonymous",
) -> ChatResponse:
    """
    Resume agent execution from the last checkpoint.

    Useful for human-in-the-loop scenarios where execution was paused
    for user feedback.

    Args:
        thread_id: Thread to resume
        user_id: User identifier

    Returns:
        ChatResponse from resumed execution

    Example:
        >>> # Agent paused for feedback
        >>> response = await resume_agent("thread_123")
        >>> print(response.content)
    """
    # Validate thread_id
    try:
        thread_id_uuid = validate_thread_id(thread_id)
        thread_id_str = str(thread_id_uuid)
    except ValueError as e:
        logger.error(f"Invalid thread_id provided: {e}")
        return ChatResponse(
            content=f"Invalid thread_id: {str(e)}",
            sources=[],
            metadata={"error": str(e)}
        )

    logger.info(f"Resuming agent workflow for thread {thread_id_str}")

    config = {
        "configurable": {
            "thread_id": thread_id_str,
            "user_id": user_id,
        }
    }

    try:
        # Get compiled graph with checkpointer
        graph = await get_graph()

        # Resume from checkpoint by passing None as input
        # (LangGraph will use last checkpoint state)
        final_state = await graph.ainvoke(None, config=config)

        # Build response
        response = ChatResponse(
            content=final_state.get(
                "generated_response", "No response generated."),
            sources=final_state.get("sources", []),
            metadata={
                "thread_id": thread_id_str,
                "resumed": True,
                **final_state.get("metadata", {}),
            }
        )

        logger.info(f"Resumed workflow complete for thread {thread_id_str}")
        return response

    except Exception as e:
        logger.error(f"Resume failed: {e}", exc_info=True)
        return ChatResponse(
            content=f"Failed to resume: {str(e)}",
            sources=[],
            metadata={"thread_id": thread_id_str, "error": str(e)}
        )


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "graph",  # For LangGraph Studio (no checkpointing)
    "get_graph",  # For production runtime (with checkpointing)
    "run_agent",
    "stream_agent",
    "get_checkpoint",
    "resume_agent",
]
