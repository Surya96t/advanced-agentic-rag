"""
LangGraph StateGraph definition and compilation.

This module assembles the complete agentic RAG workflow graph with:
- 5 agent nodes (router, query_expander, retriever, generator, validator)
- Cyclic validation loop with retry logic
- PostgreSQL checkpointing for persistence
- LangSmith tracing for observability
- Multi-mode streaming support
"""

import asyncio
import time
from typing import AsyncIterator
from uuid import UUID, uuid4

from langgraph.graph import END, START, StateGraph

from app.agents.nodes import (
    generator_node,
    query_expander_node,
    query_rewriter_node,
    retriever_node,
    router_node,
    validator_node,
)
from app.agents.nodes.classifier import classify_query

# Import new conversational nodes
from app.agents.nodes.context_loader import load_conversation_context
from app.agents.nodes.simple_answer import generate_simple_answer
from app.agents.state import AgentState, create_initial_state
from app.core.config import settings
from app.schemas.chat import ChatResponse
from app.schemas.events import (
    AgentCompleteEvent,
    AgentErrorEvent,
    AgentStartEvent,
    CitationEvent,
    CitationMapEvent,
    ContextStatusEvent,
    ConversationSummaryEvent,
    EndEvent,
    QueryClassificationEvent,
    SSEEventType,
    ThinkingEvent,
    TokenEvent,
    ValidationEvent,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ============================================================================
# Graph Construction
# ============================================================================


def build_graph() -> StateGraph:
    """
    Build the complete LangGraph StateGraph for conversational agentic RAG.

    Graph Flow (Conversational):
    1. START → context_loader (load/trim conversation history)
    2. context_loader → classifier (classify query type)
    3. classifier → (COMMAND decides) → simple_answer OR router
       - simple/conversational_followup → simple_answer → END
       - complex_standalone → router (RAG pipeline)
    4. router → (COMMAND decides) → retriever OR query_expander
    5. query_expander → retriever
    6. retriever → generator
    7. generator → validator
    8. validator → (COMMAND decides) → END OR query_expander (retry)

    Returns:
        Compiled StateGraph with checkpointing and tracing enabled
    """
    logger.info("Building LangGraph StateGraph for conversational agentic RAG")

    # Create graph builder
    builder = StateGraph(AgentState)

    # Add conversational nodes (new)
    logger.debug("Adding conversational nodes to graph")
    builder.add_node("context_loader", load_conversation_context)
    builder.add_node("classifier", classify_query)
    builder.add_node("simple_answer", generate_simple_answer)
    builder.add_node("query_rewriter", query_rewriter_node)

    # Add existing RAG nodes
    logger.debug("Adding RAG nodes to graph")
    builder.add_node("router", router_node)
    builder.add_node("query_expander", query_expander_node)
    builder.add_node("retriever", retriever_node)
    builder.add_node("generator", generator_node)
    builder.add_node("validator", validator_node)

    # Add edges
    logger.debug("Adding edges to graph")

    # Conversational flow (entry point)
    builder.add_edge(START, "context_loader")
    builder.add_edge("context_loader", "classifier")

    # Classifier uses Command pattern to route:
    # - simple/conversational_followup → simple_answer
    # - complex_standalone → router
    # (No explicit conditional edge needed, Command handles it)

    # Simple answer path (bypasses RAG pipeline)
    builder.add_edge("simple_answer", END)

    # Conversational follow-up path: rewrite → router → RAG pipeline
    builder.add_edge("query_rewriter", "router")

    # RAG pipeline (for complex queries)
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

    logger.info("Conversational graph construction complete")
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
        # FIXED: Using Supabase Session Pooler (port 5432) instead of Transaction Pooler (port 6543)
        # Session pooler supports prepared statements and maintains connection state
        # This eliminates the "prepared statement already exists" error
        conn_string = settings.supabase_connection_string

        logger.debug(
            "Using Supabase Session Pooler for checkpointing (supports prepared statements)"
        )

        # from_conn_string returns an async context manager
        checkpointer = AsyncPostgresSaver.from_conn_string(conn_string=conn_string)

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
logger.info("✅ Studio graph compiled (use get_graph() for production with checkpointing)")


def get_graph(checkpointer=None):
    """
    Get the compiled LangGraph with optional checkpointer for production use.

    This function compiles the graph with the provided checkpointer instance,
    which should be managed by the FastAPI application lifecycle.

    Args:
        checkpointer: Optional AsyncPostgresSaver instance from app.state.
                     If None, graph is compiled without checkpointing.

    Returns:
        Compiled StateGraph with or without checkpointing

    Note:
        - For LangGraph Studio: use the module-level `graph` variable
        - For production runtime: pass checkpointer from app.state
        - Checkpointer lifecycle is managed by FastAPI lifespan events
    """
    if checkpointer is None:
        logger.info("Compiling graph without checkpointing")
        builder = build_graph()
        return builder.compile()

    logger.info("Compiling graph with checkpointing enabled")
    builder = build_graph()
    compiled = builder.compile(checkpointer=checkpointer)
    logger.info("✅ Graph compiled successfully with checkpointing")
    return compiled


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
    checkpointer=None,
) -> ChatResponse:
    """
    Run the agentic RAG workflow and return final response.

    This is a simple invoke call that blocks until completion.
    Use `stream_agent()` for real-time streaming.

    Args:
        query: User's question
        thread_id: Optional conversation thread ID for checkpointing
        user_id: User identifier for RLS in database
        checkpointer: Optional checkpointer instance from app.state

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
            content=f"Invalid thread_id: {str(e)}", sources=[], metadata={"error": str(e)}
        )

    logger.info(f"Running agent workflow for query: {query[:100]}...")
    logger.debug(f"Thread ID: {thread_id}, User ID: {user_id}")

    # Create initial state with user_id for ownership tracking
    initial_state = create_initial_state(query, user_id=user_id)

    # Configuration for LangGraph execution
    config = {
        "configurable": {
            "thread_id": str(thread_id),
            "user_id": user_id,
        }
    }

    try:
        # Get compiled graph with checkpointer
        graph_instance = get_graph(checkpointer=checkpointer)

        # Invoke graph (blocks until completion)
        invoke_start = time.time()
        final_state = await graph_instance.ainvoke(initial_state, config=config)
        total_duration_ms = int((time.time() - invoke_start) * 1000)

        # Derive which nodes executed from populated state fields.
        # Branch on pipeline_path since both paths set generated_response and
        # retrieved_chunks is initialised to [] (so `is not None` is always True).
        node_executions: list[str] = ["context_loader", "classifier"]
        if final_state.get("pipeline_path") == "simple":
            node_executions.append("simple_answer")
        else:
            # RAG path
            if final_state.get("query_complexity"):
                node_executions.append("router")
            if final_state.get("expanded_queries"):
                node_executions.append("query_expander")
            if final_state.get("retrieved_chunks"):  # truthy: non-empty list
                node_executions.append("retriever")
            if final_state.get("generated_response"):
                node_executions.extend(["generator", "validator"])

        # Build response from final state
        response = ChatResponse(
            thread_id=thread_id,
            content=final_state.get("generated_response", "No response generated."),
            sources=final_state.get("sources", []),
            metadata={
                "thread_id": str(thread_id),
                "query": query,
                "complexity": final_state.get("query_complexity", "unknown"),
                "validation": final_state.get("validation_result", {}),
                "total_duration_ms": total_duration_ms,
                "node_executions": node_executions,
                **final_state.get("metadata", {}),
            },
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
            },
        )


async def stream_agent(
    query: str,
    thread_id: str | UUID | None = None,
    user_id: str = "anonymous",
    checkpointer=None,
) -> AsyncIterator[dict]:
    """
    Stream agent execution with real-time SSE events and token-by-token streaming.

    Emits events for:
    - Agent node starts/completions
    - Progress updates from nodes
    - LLM token streaming (token-by-token from generator)
    - Citation discoveries
    - Validation results
    - Final completion

    Args:
        query: User's question
        thread_id: Optional conversation thread ID
        user_id: User identifier for RLS
        checkpointer: Optional checkpointer instance from app.state

    Yields:
        SSE event dictionaries with "event" and "data" keys

    Example:
        >>> async for event in stream_agent("How does Clerk work?"):
        ...     print(f"{event['event']}: {event['data']}")
        agent_start: {"node": "router", ...}
        progress: {"message": "Analyzing query...", ...}
        token: {"token": "To", "model": "gpt-4o-mini"}
        token: {"token": " integrate", "model": "gpt-4o-mini"}
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
            ).model_dump_json(exclude_none=True),
        }
        return

    logger.info(f"Streaming agent workflow for query: {query[:100]}...")
    logger.debug(f"Thread ID: {thread_id}, User ID: {user_id}")

    # Create initial state with user_id for ownership tracking
    initial_state = create_initial_state(query, user_id=user_id)

    # Configuration
    config = {
        "configurable": {
            "thread_id": str(thread_id),
            "user_id": user_id,
        }
    }

    # Track current node for event correlation
    current_node: str | None = None
    # attempt/max_attempts tracked for ThinkingEvent emissions on node transitions.
    attempt: int = 1
    max_attempts: int = 1 + settings.validation_max_retries  # initial + retries

    try:
        # Get compiled graph with checkpointer
        graph_instance = get_graph(checkpointer=checkpointer)

        # Stream with updates + messages modes.
        # Tokens for validated responses are yielded from the validator update
        # handler below (with real asyncio.sleep delays between words) so that
        # the browser receives them progressively via HTTP chunked transfer.
        async for chunk in graph_instance.astream(
            initial_state,
            config=config,
            stream_mode=["updates", "messages"],
        ):
            # chunk is always (mode, data) when multiple stream_mode values:
            # - ("updates",  {node_name: node_update})       node state changes
            # - ("messages", (AIMessageChunk, metadata))      LLM token chunks

            mode, data = chunk

            if mode == "updates":
                # Handle node state updates
                if not data:
                    continue

                # Extract node name and update
                node_name = next(iter(data.keys()))
                node_update = data[node_name]

                # Emit agent_start if new node
                if node_name != current_node:
                    if current_node:
                        # Complete previous node
                        yield {
                            "event": SSEEventType.AGENT_COMPLETE.value,
                            "data": AgentCompleteEvent(
                                agent=current_node,
                                result={},
                            ).model_dump_json(),
                        }

                    # Start new node
                    current_node = node_name
                    yield {
                        "event": SSEEventType.AGENT_START.value,
                        "data": AgentStartEvent(
                            agent=node_name,
                            message=f"Executing {node_name} node",
                        ).model_dump_json(),
                    }

                    # Emit thinking(start) when the generator begins so the
                    # frontend can show a progress indicator.
                    if node_name == "generator":
                        yield {
                            "event": SSEEventType.THINKING.value,
                            "data": ThinkingEvent(
                                status="start",
                                message="Generating response...",
                                attempt=attempt,
                                max_attempts=max_attempts,
                            ).model_dump_json(),
                        }
                    elif node_name == "validator":
                        yield {
                            "event": SSEEventType.THINKING.value,
                            "data": ThinkingEvent(
                                status="validating",
                                message="Verifying response quality...",
                                attempt=attempt,
                                max_attempts=max_attempts,
                            ).model_dump_json(),
                        }

                # Process specific update types
                # Citation events from retriever
                if node_name == "retriever" and "sources" in node_update:
                    logger.info(f"Processing {len(node_update['sources'])} sources from retriever")
                    for source in node_update["sources"]:
                        chunk_id = source.get("chunk_id")
                        document_id = source.get("document_id")
                        document_title = source.get("document_title")
                        rrf_score = source.get("score", 0.0)
                        original_score = source.get("original_score")

                        # Format original_score for logging
                        original_score_str = (
                            f"{original_score:.4f}" if original_score is not None else "N/A"
                        )

                        logger.info(
                            f"📄 Citation: chunk_id={chunk_id}, document_id={document_id}, "
                            f"title='{document_title}', rrf_score={rrf_score:.4f}, "
                            f"original_score={original_score_str}"
                        )

                        if not chunk_id or not document_id:
                            logger.warning(
                                f"Skipping citation with missing required fields: "
                                f"chunk_id={chunk_id}, document_id={document_id}"
                            )
                            continue

                        yield {
                            "event": SSEEventType.CITATION.value,
                            "data": CitationEvent(
                                chunk_id=chunk_id,
                                document_id=document_id,
                                document_title=source.get("document_title", "Unknown Document"),
                                score=rrf_score,
                                original_score=original_score,  # Include original score for display
                                source=source.get("source", "unknown"),
                                preview=source.get("content", "")[:200]
                                if source.get("content")
                                else None,
                            ).model_dump_json(exclude_none=True),
                        }
                elif node_name == "retriever":
                    logger.warning(
                        f"Retriever node update missing 'sources' field. Keys: {list(node_update.keys())}"
                    )

                # Context status events from context_loader
                if node_name == "context_loader" and "context_window_tokens" in node_update:
                    total_tokens = node_update.get("context_window_tokens", 0)
                    max_tokens = settings.max_conversation_tokens
                    message_count = len(node_update.get("messages", []))
                    remaining = max(0, max_tokens - total_tokens)
                    percentage = (total_tokens / max_tokens * 100) if max_tokens > 0 else 0

                    yield {
                        "event": SSEEventType.CONTEXT_STATUS.value,
                        "data": ContextStatusEvent(
                            total_tokens=total_tokens,
                            max_tokens=max_tokens,
                            remaining_tokens=remaining,
                            message_count=message_count,
                            percentage_used=round(percentage, 2),
                        ).model_dump_json(),
                    }

                    logger.info(
                        f"📊 Context status: {total_tokens}/{max_tokens} tokens ({percentage:.1f}%)"
                    )

                # Conversation summary events from context_loader
                if node_name == "context_loader" and "conversation_summary" in node_update:
                    summary = node_update.get("conversation_summary", "")
                    if summary:  # Only emit if there's an actual summary
                        # Estimate messages summarized vs kept
                        messages = node_update.get("messages", [])
                        messages_kept = len(messages)
                        # This is an approximation; actual count would need to be passed from context_loader
                        messages_summarized = node_update.get("messages_summarized", 0)

                        yield {
                            "event": SSEEventType.CONVERSATION_SUMMARY.value,
                            "data": ConversationSummaryEvent(
                                summary=summary,
                                # At least 1 if summary exists
                                messages_summarized=max(1, messages_summarized),
                                messages_kept=messages_kept,
                            ).model_dump_json(),
                        }

                        logger.info(f"📝 Conversation summary generated ({len(summary)} chars)")

                # Query classification events from classifier
                if node_name == "classifier" and "query_type" in node_update:
                    query_type = node_update.get("query_type", "unknown")
                    needs_retrieval = node_update.get("needs_retrieval", True)
                    pipeline_path = node_update.get("pipeline_path", "unknown")

                    # Generate reasoning from query_type
                    reasoning_map = {
                        "simple": "Simple query (greeting/thanks) - no retrieval needed",
                        "conversational_followup": "Follow-up to conversation - using context only",
                        "complex_standalone": "Complex query requiring retrieval",
                    }
                    reasoning = reasoning_map.get(query_type, "Query classification determined")

                    yield {
                        "event": SSEEventType.QUERY_CLASSIFICATION.value,
                        "data": QueryClassificationEvent(
                            query_type=query_type,
                            needs_retrieval=needs_retrieval,
                            reasoning=reasoning,
                            pipeline_path=pipeline_path,
                        ).model_dump_json(),
                    }

                    logger.info(f"🔍 Query classified: {query_type} (retrieval={needs_retrieval})")

                # Diagnostic: log the rewritten query so we can trace it
                if node_name == "query_rewriter" and "retrieval_query" in node_update:
                    rewritten = node_update["retrieval_query"]
                    logger.info(f"✏️  Query rewritten: '{rewritten[:120]}'")

                # Diagnostic: log what the router decided
                if node_name == "router" and "retrieval_query" in node_update:
                    rq = node_update["retrieval_query"]
                    cplx = node_update.get("query_complexity", "?")
                    logger.info(
                        f"🔀 Router decision: complexity={cplx}, retrieval_query='{rq[:120]}'"
                    )

                # Validation result + token streaming.
                # When the validator approves the response (or max retries
                # exhausted), it includes 'generated_response' in its update.
                # We stream the tokens here — inside the SSE async generator —
                # with real ``asyncio.sleep`` delays between words so that
                # HTTP chunked transfer delivers them progressively.
                if node_name == "validator" and "validation_result" in node_update:
                    validation = node_update["validation_result"]
                    passed = validation.get("passed", False)

                    yield {
                        "event": SSEEventType.VALIDATION.value,
                        "data": ValidationEvent(
                            passed=passed,
                            score=validation.get("score", 0.0),
                            issues=validation.get("issues", []),
                        ).model_dump_json(),
                    }

                    approved_response = node_update.get("generated_response")
                    if approved_response is not None:
                        # Validator approved (or max retries): stream tokens.
                        yield {
                            "event": SSEEventType.THINKING.value,
                            "data": ThinkingEvent(
                                status="complete",
                                message="Response ready",
                                attempt=attempt,
                                max_attempts=max_attempts,
                            ).model_dump_json(),
                        }

                        words = approved_response.split(" ")
                        for i, word in enumerate(words):
                            token = word if i == len(words) - 1 else word + " "
                            if token:
                                yield {
                                    "event": SSEEventType.TOKEN.value,
                                    "data": TokenEvent(
                                        token=token,
                                        model=settings.openai_model,
                                    ).model_dump_json(),
                                }
                                # Real delay so tokens are flushed as separate
                                # HTTP chunks — this is what makes streaming
                                # visible in the browser.
                                await asyncio.sleep(0.015)

                    elif "retry_count" in node_update and node_update["retry_count"] > 0:
                        # Validator rejected — retrying.
                        attempt = node_update["retry_count"] + 1
                        yield {
                            "event": SSEEventType.THINKING.value,
                            "data": ThinkingEvent(
                                status="retrying",
                                message=f"Improving response (attempt {attempt}/{max_attempts})...",
                                attempt=attempt,
                                max_attempts=max_attempts,
                            ).model_dump_json(),
                        }

                # Citation map event from generator — emit immediately so the
                # frontend has it before tokens start flowing from the validator.
                if node_name == "generator" and "citation_map" in node_update:
                    raw_map = node_update.get("citation_map", {})
                    if raw_map:
                        yield {
                            "event": SSEEventType.CITATION_MAP.value,
                            "data": CitationMapEvent(
                                markers={str(k): v for k, v in raw_map.items()}
                            ).model_dump_json(),
                        }
                        logger.info(f"📌 Emitted citation_map with {len(raw_map)} markers")

            elif mode == "messages":
                # simple_answer tokens — no validation loop, stream directly.
                msg_chunk, metadata = data
                node = metadata.get("langgraph_node")
                if node == "simple_answer" and hasattr(msg_chunk, "content") and msg_chunk.content:
                    yield {
                        "event": SSEEventType.TOKEN.value,
                        "data": TokenEvent(
                            token=msg_chunk.content,
                            model=settings.openai_model,
                        ).model_dump_json(),
                    }

        # Complete final node
        if current_node:
            yield {
                "event": SSEEventType.AGENT_COMPLETE.value,
                "data": AgentCompleteEvent(
                    agent=current_node,
                    result={},
                ).model_dump_json(),
            }

        # Final end event
        yield {
            "event": SSEEventType.END.value,
            "data": EndEvent(
                thread_id=str(thread_id),
                success=True,
            ).model_dump_json(exclude_none=True),
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
                ).model_dump_json(),
            }

        yield {
            "event": SSEEventType.END.value,
            "data": EndEvent(
                thread_id=str(thread_id),
                success=False,
                error=str(e),
            ).model_dump_json(exclude_none=True),
        }


async def get_checkpoint(thread_id: str | UUID, checkpointer=None) -> dict | None:
    """
    Get the latest checkpoint for a conversation thread.

    Useful for debugging or displaying conversation history.

    Args:
        thread_id: Thread identifier
        checkpointer: Optional checkpointer instance from app.state

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
        graph_instance = get_graph(checkpointer=checkpointer)

        # Get checkpoint from graph
        config = {"configurable": {"thread_id": thread_id_str}}
        state_snapshot = await graph_instance.aget_state(config)

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
    checkpointer=None,
) -> ChatResponse:
    """
    Resume agent execution from the last checkpoint.

    Useful for human-in-the-loop scenarios where execution was paused
    for user feedback.

    Args:
        thread_id: Thread to resume
        user_id: User identifier
        checkpointer: Optional checkpointer instance from app.state

    Returns:
        ChatResponse from resumed execution

    Raises:
        ValueError: If checkpointer is None (resuming requires checkpointing)

    Example:
        >>> # Agent paused for feedback
        >>> response = await resume_agent("thread_123", checkpointer=app.state.checkpointer)
        >>> print(response.content)
    """
    # Validate checkpointer is provided
    if checkpointer is None:
        error_msg = (
            f"Cannot resume agent for thread_id='{thread_id}', user_id='{user_id}': "
            "Resuming requires a compiled graph with checkpointing enabled. "
            "Please provide a checkpointer instance from app.state."
        )
        logger.error(error_msg)
        return ChatResponse(
            content="Cannot resume conversation: Checkpointing is not enabled.",
            sources=[],
            metadata={
                "error": error_msg,
                "thread_id": str(thread_id),
                "user_id": user_id,
            },
        )

    # Validate thread_id
    try:
        thread_id_uuid = validate_thread_id(thread_id)
        thread_id_str = str(thread_id_uuid)
    except ValueError as e:
        logger.error(f"Invalid thread_id provided: {e}")
        return ChatResponse(
            content=f"Invalid thread_id: {str(e)}", sources=[], metadata={"error": str(e)}
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
        graph_instance = get_graph(checkpointer=checkpointer)

        # Resume from checkpoint by passing None as input
        # (LangGraph will use last checkpoint state)
        final_state = await graph_instance.ainvoke(None, config=config)

        # Build response
        response = ChatResponse(
            content=final_state.get("generated_response", "No response generated."),
            sources=final_state.get("sources", []),
            metadata={
                "thread_id": thread_id_str,
                "resumed": True,
                **final_state.get("metadata", {}),
            },
        )

        logger.info(f"Resumed workflow complete for thread {thread_id_str}")
        return response

    except Exception as e:
        logger.error(f"Resume failed: {e}", exc_info=True)
        return ChatResponse(
            content=f"Failed to resume: {str(e)}",
            sources=[],
            metadata={"thread_id": thread_id_str, "error": str(e)},
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
