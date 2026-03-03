"""
Router node for query complexity analysis and routing.

This module analyzes the user's query to determine its complexity
and routes to the appropriate next node (retriever or query expander).
"""

import re
import time
from typing import Literal

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.types import Command

from app.agents.state import AgentState
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Confidence threshold below which we invoke the LLM for a second opinion
CONFIDENCE_THRESHOLD = 0.85

# Lightweight LLM for routing decisions (lower temp for determinism)
_router_llm = ChatOpenAI(
    model=settings.openai_model,
    temperature=0.0,
    api_key=settings.openai_api_key,
)

# Vague terms that indicate ambiguous queries
VAGUE_TERMS = {
    "issue", "issues", "problem", "problems", "error", "errors",
    "help", "trouble", "not working", "doesn't work", "won't work",
    "broken", "fix", "debug", "stuck", "failing", "failed"
}

# Common framework/tool names (partial list for named entity detection)
FRAMEWORK_NAMES = {
    "prisma", "clerk", "next.js", "nextjs", "react", "typescript",
    "javascript", "node", "python", "convex", "supabase", "langgraph",
    "langchain", "openai", "vercel", "postgres", "postgresql"
}


def analyze_query_complexity(query: str) -> tuple[Literal["simple", "complex", "ambiguous"], float]:
    """
    Analyse query complexity using heuristics and return a confidence score.

    Returns:
        Tuple of (classification, confidence) where confidence ∈ (0, 1].
        Values ≤ CONFIDENCE_THRESHOLD (0.85) trigger an async LLM fallback in
        router_node to confirm or override the classification.

    Example:
        >>> analyze_query_complexity("How do I install Prisma?")
        ('simple', 0.85)
        >>> analyze_query_complexity("user sync issues")
        ('ambiguous', 0.95)
    """
    query_lower = query.lower()
    words = query_lower.split()

    # Check for vague terms (highest priority, high confidence)
    if any(term in query_lower for term in VAGUE_TERMS):
        logger.info(f"Query classified as ambiguous (vague terms): {query[:50]}...")
        return "ambiguous", 0.95

    # Count framework/tool mentions
    framework_count = sum(1 for name in FRAMEWORK_NAMES if name in query_lower)

    # Count question marks
    question_marks = query.count("?")

    # Check for boolean operators
    has_boolean_operators = bool(
        re.search(r'\b(and|or|plus|along with)\b', query_lower)
    )

    # Assign confidence based on how many strong signals are present
    complex_signals = (
        (framework_count >= 2, 0.90),
        (question_marks >= 2, 0.88),
        (has_boolean_operators, 0.87),
        (len(words) > 15, 0.82),
    )

    # Use the highest-confidence signal that fires
    for condition, confidence in sorted(complex_signals, key=lambda x: -x[1]):
        if condition:
            logger.info(f"Query classified as complex (confidence={confidence}): {query[:50]}...")
            return "complex", confidence

    # Default: simple — moderate confidence (may trigger LLM fallback)
    logger.info(f"Query classified as simple (confidence=0.85): {query[:50]}...")
    return "simple", 0.85


async def _llm_classify_complexity(query: str) -> Literal["simple", "complex", "ambiguous"]:
    """
    Use the LLM to classify query complexity when heuristics are uncertain.

    Returns one of: "simple", "complex", "ambiguous".
    Falls back to "simple" on any error.
    """
    system = (
        "You are a query routing assistant. Classify the user's query into exactly ONE category:\n"
        "- simple: a direct, single-concept question that can be answered with one focused document search\n"
        "- complex: requires multiple concepts, comparisons, or sub-queries to answer fully\n"
        "- ambiguous: vague or underspecified, needs clarification or hypothetical expansion\n"
        "Respond with ONLY the single word: simple, complex, or ambiguous."
    )
    try:
        response = await _router_llm.ainvoke([
            SystemMessage(content=system),
            HumanMessage(content=f"Query: {query}"),
        ])
        label = response.content.strip().lower()
        if label in ("simple", "complex", "ambiguous"):
            return label  # type: ignore[return-value]
        return "simple"
    except Exception as e:
        logger.warning(f"LLM router fallback failed: {e}, defaulting to simple")
        return "simple"


async def router_node(state: AgentState) -> Command[Literal["retriever", "query_expander"]]:
    """
    Router node that analyzes query complexity and routes to next node.

    Routing logic:
    - Simple queries → directly to retriever (skip expansion)
    - Complex queries → to query_expander for sub-query decomposition
    - Ambiguous queries → to query_expander for HyDE expansion

    Args:
        state: Current agent state with original_query

    Returns:
        Command object with state update and goto directive

    Example:
        >>> state = {"original_query": "How do I install Prisma?"}
        >>> cmd = router_node(state)
        >>> cmd.goto
        'retriever'
        >>> cmd.update["query_complexity"]
        'simple'
    """
    start_time = time.time()
    logger.info("⏱️  ROUTER NODE: Starting query complexity analysis")

    # Extract query from state (either from original_query or last message)
    query: str = ""

    if "original_query" in state and state["original_query"]:
        query = state["original_query"]
    elif "messages" in state and state["messages"]:
        # Extract query from last user message
        last_message = state["messages"][-1]

        # Handle different message formats from Studio/LangChain
        if hasattr(last_message, 'content'):
            # Standard LangChain message object
            content = last_message.content

            # If content is a list of message parts (e.g., [{'type': 'text', 'text': '...'}])
            if isinstance(content, list):
                # Extract text from all text parts
                text_parts = [
                    part.get('text', '') if isinstance(
                        part, dict) else str(part)
                    for part in content
                    if (isinstance(part, dict) and part.get('type') == 'text') or not isinstance(part, dict)
                ]
                query = ' '.join(text_parts).strip()
            else:
                # Content is already a string
                query = str(content).strip()
        else:
            # Fallback for non-standard message format
            query = str(last_message).strip()
    else:
        raise ValueError(
            "No query found in state. Provide either 'original_query' or 'messages'.")

    # Ensure query is not empty
    if not query:
        raise ValueError(
            "Extracted query is empty. Please provide a valid question.")

    logger.info(
        f"Router node: Analyzing query complexity for: {query[:100]}...")

    # Analyse complexity (returns classification + confidence)
    complexity, confidence = analyze_query_complexity(query)

    # LLM fallback when heuristic confidence is too low
    if confidence <= CONFIDENCE_THRESHOLD:
        logger.info(
            f"Heuristic confidence {confidence:.2f} ≤ {CONFIDENCE_THRESHOLD}, "
            f"invoking LLM to confirm classification (heuristic: {complexity})"
        )
        llm_complexity = await _llm_classify_complexity(query)
        if llm_complexity != complexity:
            logger.info(
                f"LLM overrode heuristic: {complexity} → {llm_complexity}"
            )
        complexity = llm_complexity

    # Determine next node
    if complexity == "simple":
        next_node = "retriever"
        logger.info("Routing to retriever (simple query, no expansion needed)")
    else:
        next_node = "query_expander"
        logger.info(f"Routing to query_expander ({complexity} query)")

    elapsed_time = time.time() - start_time
    logger.info(
        f"⏱️  ROUTER NODE: Completed in {elapsed_time:.3f}s | Complexity: {complexity} | Next: {next_node}")

    # Return Command with state update and routing
    return Command(
        update={
            "query_complexity": complexity,
            "original_query": query  # Store query in state for downstream nodes
        },
        goto=next_node
    )


def route_after_classification(state: AgentState) -> str:
    """
    Route based on query classification.

    This is used in the conversational agent graph to route queries
    after they've been classified by the classifier node.

    Routing logic:
    - simple queries (no retrieval needed) → "simple_answer"
    - conversational_followup or complex_standalone → "retrieval"

    Args:
        state: Current agent state with query_type and needs_retrieval

    Returns:
        Next node name: "simple_answer" or "retrieval"

    Example:
        >>> state = {"query_type": "simple", "needs_retrieval": False}
        >>> route_after_classification(state)
        'simple_answer'
        >>> state = {"query_type": "complex_standalone", "needs_retrieval": True}
        >>> route_after_classification(state)
        'retrieval'
    """
    query_type = state.get("query_type", "complex_standalone")
    needs_retrieval = state.get("needs_retrieval", True)

    # Simple queries go directly to simple_answer node
    if query_type == "simple" or not needs_retrieval:
        logger.info("Routing to simple_answer (no retrieval needed)")
        return "simple_answer"

    # All other queries go through retrieval pipeline
    logger.info(f"Routing to retrieval ({query_type}, needs retrieval)")
    return "retrieval"
