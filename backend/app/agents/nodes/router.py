"""
Router node for query complexity analysis and routing.

This module analyzes the user's query to determine its complexity
and routes to the appropriate next node (retriever or query expander).
"""

import re
import time
from typing import Literal

from langgraph.types import Command

from app.agents.state import AgentState
from app.utils.logger import get_logger

logger = get_logger(__name__)

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


def analyze_query_complexity(query: str) -> Literal["simple", "complex", "ambiguous"]:
    """
    Analyze query complexity using heuristics.

    Classification logic:
    - Simple: Direct, single-concept queries (e.g., "How do I install Prisma?")
    - Complex: Multi-concept queries requiring decomposition (e.g., "How do I integrate Clerk with Prisma?")
    - Ambiguous: Vague queries needing HyDE expansion (e.g., "user sync issues")

    Heuristics:
    1. Vague terms detection → ambiguous
    2. Multiple framework names → complex
    3. Multiple question marks → complex
    4. Boolean operators (AND/OR) → complex
    5. Long queries (>15 words) → complex
    6. Otherwise → simple

    Args:
        query: User's question

    Returns:
        Query complexity classification

    Example:
        >>> analyze_query_complexity("How do I install Prisma?")
        'simple'
        >>> analyze_query_complexity("How do I integrate Clerk with Prisma?")
        'complex'
        >>> analyze_query_complexity("user sync issues")
        'ambiguous'
    """
    query_lower = query.lower()
    words = query_lower.split()

    # Check for vague terms (highest priority)
    if any(term in query_lower for term in VAGUE_TERMS):
        logger.info(
            f"Query classified as ambiguous (vague terms detected): {query[:50]}...")
        return "ambiguous"

    # Count framework/tool mentions
    framework_count = sum(1 for name in FRAMEWORK_NAMES if name in query_lower)

    # Count question marks
    question_marks = query.count("?")

    # Check for boolean operators
    has_boolean_operators = bool(
        re.search(r'\b(and|or|plus|along with)\b', query_lower)
    )

    # Complex if:
    # - Multiple frameworks mentioned (2+)
    # - Multiple questions (2+)
    # - Boolean operators present
    # - Long query (>15 words)
    if (
        framework_count >= 2
        or question_marks >= 2
        or has_boolean_operators
        or len(words) > 15
    ):
        logger.info(f"Query classified as complex: {query[:50]}...")
        return "complex"

    # Default to simple
    logger.info(f"Query classified as simple: {query[:50]}...")
    return "simple"


def router_node(state: AgentState) -> Command[Literal["retriever", "query_expander"]]:
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

    # Analyze complexity
    complexity = analyze_query_complexity(query)

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
