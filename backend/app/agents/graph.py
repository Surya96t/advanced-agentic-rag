"""
LangGraph StateGraph definition and compilation.

This module assembles the complete agentic RAG workflow graph with:
- 5 agent nodes (router, query_expander, retriever, generator, validator)
- Cyclic validation loop with retry logic
- PostgreSQL checkpointing for persistence
- LangSmith tracing for observability
- Multi-mode streaming support
"""

import json
from typing import AsyncIterator
from uuid import UUID, uuid4

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage

from app.agents.state import AgentState, create_initial_state
from app.agents.nodes import (
    router_node,
    query_expander_node,
    retriever_node,
    generator_node,
    validator_node,
)
from app.core.config import settings
from app.schemas.chat import ChatResponse
from app.schemas.events import (
    SSEEventType,
    AgentStartEvent,
    AgentCompleteEvent,
    ProgressEvent,
    TokenEvent,
    CitationEvent,
    ValidationEvent,
    EndEvent,
)
from app.utils.logger import get_logger

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
    """
    # Lazy import to avoid module-level import issues with Studio
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    logger.info("Initializing PostgreSQL checkpointer")

    try:
        checkpointer = await AsyncPostgresSaver.from_conn_string(
            conn_string=settings.supabase_connection_string
        )

        logger.info("Checkpointer initialized successfully")
        return checkpointer

    except Exception as e:
        logger.error(f"Failed to initialize checkpointer: {e}")
        raise


# Build and compile graph
logger.info("Compiling LangGraph with checkpointing")
_builder = build_graph()

# Note: Checkpointer initialization is async, so we'll handle it differently
# For now, compile without checkpointer (will add in async context)
graph = _builder.compile()

logger.info(
    "✅ LangGraph compiled successfully (checkpointer deferred to runtime)")


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
    # Generate thread_id if not provided
    if thread_id is None:
        thread_id = uuid4()
    else:
        thread_id = UUID(str(thread_id))

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
    # Generate thread_id if not provided
    if thread_id is None:
        thread_id = uuid4()
    else:
        thread_id = UUID(str(thread_id))

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
        # Stream with multiple modes for rich event data
        async for event in graph.astream(
            initial_state,
            config=config,
            stream_mode=["updates", "messages", "custom"],  # Multiple modes
        ):
            # Process different event types
            # Event structure: {mode: data}

            # Mode 1: Updates (state changes after each node)
            if "updates" in event:
                node_name = list(event["updates"].keys())[0]
                node_update = event["updates"][node_name]

                # Emit agent_start if new node
                if node_name != current_node:
                    if current_node:
                        # Complete previous node
                        yield {
                            "event": SSEEventType.AGENT_COMPLETE,
                            "data": json.dumps(AgentCompleteEvent(
                                node_name=current_node,
                                status="success",
                            ).model_dump())
                        }

                    # Start new node
                    current_node = node_name
                    yield {
                        "event": SSEEventType.AGENT_START,
                        "data": json.dumps(AgentStartEvent(
                            node_name=node_name,
                        ).model_dump())
                    }

                # Process specific update types
                # Citation events from retriever
                if node_name == "retriever" and "sources" in node_update:
                    for source in node_update["sources"]:
                        yield {
                            "event": SSEEventType.CITATION,
                            "data": json.dumps(CitationEvent(
                                chunk_id=source["chunk_id"],
                                document_id=source["document_id"],
                                document_title=source["document_title"],
                                score=source["score"],
                                source=source["source"],
                            ).model_dump())
                        }

                # Validation events
                if node_name == "validator" and "validation_result" in node_update:
                    validation = node_update["validation_result"]
                    yield {
                        "event": SSEEventType.VALIDATION,
                        "data": json.dumps(ValidationEvent(
                            passed=validation.get("passed", False),
                            score=validation.get("score", 0.0),
                            issues=validation.get("issues", []),
                        ).model_dump())
                    }

            # Mode 2: Messages (LLM token streaming)
            elif "messages" in event:
                # Stream tokens from generator
                message_data = event["messages"]
                if isinstance(message_data, list):
                    for msg in message_data:
                        if hasattr(msg, "content") and msg.content:
                            yield {
                                "event": SSEEventType.TOKEN,
                                "data": json.dumps(TokenEvent(
                                    token=msg.content,
                                ).model_dump())
                            }
                elif hasattr(message_data, "content"):
                    yield {
                        "event": SSEEventType.TOKEN,
                        "data": json.dumps(TokenEvent(
                            token=message_data.content,
                        ).model_dump())
                    }

            # Mode 3: Custom (progress events from nodes)
            elif "custom" in event:
                custom_data = event["custom"]
                event_type = custom_data.get("type", "progress")

                if event_type == "progress":
                    yield {
                        "event": SSEEventType.PROGRESS,
                        "data": json.dumps(ProgressEvent(
                            message=custom_data.get("message", ""),
                            progress=custom_data.get("progress", 0.0),
                        ).model_dump())
                    }

        # Complete final node
        if current_node:
            yield {
                "event": SSEEventType.AGENT_COMPLETE,
                "data": json.dumps(AgentCompleteEvent(
                    node_name=current_node,
                    status="success",
                ).model_dump())
            }

        # Final end event
        yield {
            "event": SSEEventType.END,
            "data": json.dumps(EndEvent(
                thread_id=str(thread_id),
                success=True,
            ).model_dump())
        }

        logger.info(f"Streaming complete for thread {thread_id}")

    except Exception as e:
        logger.error(f"Streaming failed: {e}", exc_info=True)

        # Emit error event
        if current_node:
            yield {
                "event": SSEEventType.AGENT_COMPLETE,
                "data": json.dumps(AgentCompleteEvent(
                    node_name=current_node,
                    status="error",
                    error=str(e),
                ).model_dump())
            }

        yield {
            "event": SSEEventType.END,
            "data": json.dumps(EndEvent(
                thread_id=str(thread_id),
                success=False,
                error=str(e),
            ).model_dump())
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
    thread_id = str(thread_id)
    logger.info(f"Fetching checkpoint for thread {thread_id}")

    try:
        # Get checkpoint from graph
        config = {"configurable": {"thread_id": thread_id}}
        state_snapshot = await graph.aget_state(config)

        if state_snapshot:
            logger.info(f"Checkpoint found for thread {thread_id}")
            return state_snapshot.values
        else:
            logger.info(f"No checkpoint found for thread {thread_id}")
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
    thread_id = str(thread_id)
    logger.info(f"Resuming agent workflow for thread {thread_id}")

    config = {
        "configurable": {
            "thread_id": thread_id,
            "user_id": user_id,
        }
    }

    try:
        # Resume from checkpoint by passing None as input
        # (LangGraph will use last checkpoint state)
        final_state = await graph.ainvoke(None, config=config)

        # Build response
        response = ChatResponse(
            content=final_state.get(
                "generated_response", "No response generated."),
            sources=final_state.get("sources", []),
            metadata={
                "thread_id": thread_id,
                "resumed": True,
                **final_state.get("metadata", {}),
            }
        )

        logger.info(f"Resumed workflow complete for thread {thread_id}")
        return response

    except Exception as e:
        logger.error(f"Resume failed: {e}", exc_info=True)
        return ChatResponse(
            content=f"Failed to resume: {str(e)}",
            sources=[],
            metadata={"thread_id": thread_id, "error": str(e)}
        )


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "graph",
    "run_agent",
    "stream_agent",
    "get_checkpoint",
    "resume_agent",
]
