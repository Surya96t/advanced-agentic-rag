"""
Agent state models for LangGraph workflows.

This module defines the state schema used by the agentic RAG workflow,
including TypedDict definitions, reducer functions, and helper utilities.
"""

from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

from app.schemas.retrieval import SearchResult


def add_search_results(existing: list[SearchResult], new: list[SearchResult]) -> list[SearchResult]:
    """
    Reducer function for appending search results without duplicates.

    Deduplicates by chunk_id, keeping the highest score for each chunk.

    Args:
        existing: Current list of search results
        new: New search results to add

    Returns:
        Combined list with duplicates removed
    """
    # Build dict of chunk_id -> SearchResult (keeping highest score)
    results_dict: dict[str, SearchResult] = {}

    for result in existing + new:
        chunk_id = str(result.chunk_id)
        if chunk_id not in results_dict or result.score > results_dict[chunk_id].score:
            results_dict[chunk_id] = result

    # Return sorted by score (descending)
    return sorted(results_dict.values(), key=lambda x: x.score, reverse=True)


def add_sources(existing: list[dict], new: list[dict]) -> list[dict]:
    """
    Reducer function for appending source citations without duplicates.

    Deduplicates by document_id.

    Args:
        existing: Current list of sources
        new: New sources to add

    Returns:
        Combined list with duplicates removed
    """
    # Build dict of document_id -> source
    sources_dict: dict[str, dict] = {}

    for source in existing + new:
        doc_id = source.get("document_id")
        if doc_id and doc_id not in sources_dict:
            sources_dict[doc_id] = source

    return list(sources_dict.values())


class AgentState(TypedDict, total=False):
    """
    State schema for the agentic RAG workflow.

    This TypedDict defines all fields used by the LangGraph state machine.
    Fields with Annotated types use reducer functions to merge updates.

    Attributes:
        messages: Conversation history (required, uses add_messages reducer)
        original_query: User's original question (required)
        query: Current working query (may be expanded/rewritten for better retrieval)
        expanded_queries: List of expanded/decomposed queries
        query_complexity: Classification of query type
        query_type: Conversational classification ("simple" | "conversational_followup" | "complex_standalone")
        needs_retrieval: Whether RAG retrieval is needed for this query
        conversation_summary: Summary of older conversation messages
        context_window_tokens: Current token count in conversation context
        pipeline_path: Which pipeline path was taken ("simple" | "complex")
        retrieved_chunks: Search results from retrieval
        generated_response: LLM-generated answer
        validation_result: Quality validation results
        retry_count: Number of validation retries attempted
        sources: Source citations for response
        metadata: Execution metadata (timing, costs, etc.)
        feedback_requested: Whether human feedback is needed

    Learning Note:
        - TypedDict with total=False makes all fields optional except those explicitly required
        - Annotated types like Annotated[list, add_messages] use reducer functions
        - Reducers control how state updates are merged (append, replace, etc.)
    """
    # Conversation history (required field, uses LangChain's message reducer)
    messages: Annotated[list[AnyMessage], add_messages]

    # User context (for ownership and RLS)
    user_id: str

    # Query processing (original_query is required)
    original_query: str
    retrieval_query: str  # Cleaned/rewritten query used for retrieval (format instructions stripped)
    query: str  # Current working query (may be expanded/rewritten)
    expanded_queries: list[str]
    query_complexity: Literal["simple", "complex", "ambiguous"]

    # Conversational features (NEW)
    query_type: Literal["simple",
                        "conversational_followup", "complex_standalone"]
    needs_retrieval: bool
    conversation_summary: str
    context_window_tokens: int
    pipeline_path: Literal["simple", "complex"]

    # Retrieval results (replaced each run — no reducer so prior-run chunks don't leak)
    retrieved_chunks: list[SearchResult]

    # Generation
    generated_response: str
    format_instructions: str  # Format/style directives extracted from user query (e.g. "briefly", "in bullet points")
    citation_map: dict[str, Any]  # Inline citation markers {"1": {chunk_id, document_id, ...}}
    citations: list[dict]  # Full citation details from generator for persistence

    # Validation
    validation_result: dict[str, Any]
    retry_count: int

    # Output (replaced each run — no reducer so prior-run sources don't leak)
    sources: list[dict]
    metadata: dict[str, Any]

    # Human-in-the-loop
    feedback_requested: bool


def create_initial_state(query: str, user_id: str = "anonymous") -> AgentState:
    """
    Create initial state for a new agent run.

    Args:
        query: User's question
        user_id: User identifier for ownership tracking (required for persistence)

    Returns:
        AgentState with query, user_id, and initial HumanMessage set

    Example:
        >>> state = create_initial_state("How do I use Prisma?", user_id="user_123")
        >>> state["original_query"]
        'How do I use Prisma?'
        >>> state["user_id"]
        'user_123'
        >>> state["messages"][0].content
        'How do I use Prisma?'
        >>> state["retry_count"]
        0
    """
    # Import here to avoid circular dependency
    from langchain_core.messages import HumanMessage

    return AgentState(
        original_query=query,
        query=query,  # Set query for classifier and other nodes
        user_id=user_id,  # CRITICAL: Set user_id for RLS and ownership
        # Add user's message to history
        messages=[HumanMessage(content=query)],
        expanded_queries=[],
        retrieved_chunks=[],
        retry_count=0,
        sources=[],
        # Initialize conversational fields with defaults
        query_type="complex_standalone",  # Default assumption until classifier runs
        needs_retrieval=True,  # Default to retrieval unless classifier says otherwise
        conversation_summary="",
        context_window_tokens=0,
        pipeline_path="complex",  # Default path
        metadata={
            "start_time": None,
            "end_time": None,
            "nodes_executed": [],
            "total_tokens": 0,
            "total_cost": 0.0,
        },
        feedback_requested=False,
    )


def update_metadata(state: AgentState, **kwargs: Any) -> dict[str, Any]:
    """
    Update metadata field with new values.

    Merges new metadata into existing metadata dict.

    Args:
        state: Current agent state
        **kwargs: Metadata fields to update

    Returns:
        State update dict containing merged metadata

    Example:
        >>> update = update_metadata(state, total_tokens=150, node_latency_ms=245)
        >>> update["metadata"]["total_tokens"]
        150
    """
    current_metadata = state.get("metadata", {})
    updated_metadata = {**current_metadata, **kwargs}

    return {"metadata": updated_metadata}
