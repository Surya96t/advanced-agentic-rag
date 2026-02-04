"""
Query classifier node for determining routing strategy.

This node uses an LLM with structured output to classify queries as:
- simple: Greetings, thanks, meta questions (no retrieval needed)
- conversational_followup: References previous messages (minimal retrieval)
- complex_standalone: Technical questions requiring full RAG pipeline
"""

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.types import Command
from pydantic import BaseModel, Field

from app.agents.state import AgentState
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class QueryClassification(BaseModel):
    """Structured output for query classification."""

    query_type: str = Field(
        description="Type: 'simple', 'conversational_followup', or 'complex_standalone'"
    )
    needs_retrieval: bool = Field(description="Whether retrieval is needed")
    reasoning: str = Field(description="Brief explanation of classification")


def format_messages_for_classifier(messages: list) -> str:
    """
    Format recent messages for classification context.

    Args:
        messages: Recent message history

    Returns:
        Formatted conversation string (excludes current query)
    """
    lines = []
    for msg in messages[:-1]:  # Exclude current query
        if isinstance(msg, HumanMessage):
            lines.append(f"User: {msg.content}")
        elif isinstance(msg, AIMessage):
            # Truncate long AI responses
            content = msg.content[:200] + \
                "..." if len(msg.content) > 200 else msg.content
            lines.append(f"Assistant: {content}")
    return "\n".join(lines) if lines else "No previous context"


async def classify_query(state: AgentState) -> dict[str, Any]:
    """
    Classify the user's query to determine routing.

    Uses LLM with structured output for reliable classification.

    Classification types:
    1. simple - Greetings, thanks, meta questions → no retrieval
    2. conversational_followup - Refers to previous context → maybe retrieval
    3. complex_standalone - Technical questions → full retrieval

    Args:
        state: Current agent state with query and message history

    Returns:
        State update dict with query_type, needs_retrieval, and pipeline_path

    Example:
        >>> state = {"query": "hi", "messages": []}
        >>> result = await classify_query(state)
        >>> result["query_type"]
        'simple'
        >>> result["needs_retrieval"]
        False
    """
    query = state.get("query") or state.get("original_query", "")
    messages = state.get("messages", [])

    logger.info(f"🔍 CLASSIFIER: Classifying query: '{query[:50]}...'")

    # Get last few messages for context
    recent_context = messages[-5:] if len(messages) > 5 else messages
    context_str = format_messages_for_classifier(recent_context)

    # Use structured output for reliable classification
    llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=0,
        api_key=settings.openai_api_key,
    ).with_structured_output(QueryClassification)

    classification_prompt = f"""Classify this user query to determine how to handle it.

Context (recent messages):
{context_str}

Current query: {query}

Classification rules:
1. "simple" - Greetings, thanks, meta questions, very short responses → no retrieval
   Examples: "hi", "hello", "thanks", "what can you help with?"
   
2. "conversational_followup" - Refers to previous messages ("tell me more", "what about X?") → minimal retrieval
   Examples: "tell me more about that", "what else?", "can you give an example?"
   
3. "complex_standalone" - Technical questions, new topics, requires documentation → full retrieval
   Examples: "how do I implement OAuth in FastAPI?", "explain async/await in Python"

More examples:
- "hi" → simple, no retrieval
- "thanks!" → simple, no retrieval
- "tell me more about that" → conversational_followup, maybe retrieval
- "how do I implement OAuth in FastAPI?" → complex_standalone, needs retrieval
- "what about error handling?" (after discussing FastAPI) → conversational_followup, needs retrieval

Classify the current query."""

    try:
        result: QueryClassification = await llm.ainvoke(
            [
                SystemMessage(
                    content="You are a query classification expert."),
                HumanMessage(content=classification_prompt),
            ]
        )

        logger.info(
            f"  ↳ Classification: {result.query_type} | "
            f"Needs retrieval: {result.needs_retrieval} | "
            f"Reasoning: {result.reasoning}"
        )

        # Determine routing based on classification
        if result.query_type == "simple" or not result.needs_retrieval:
            # Route to simple_answer (bypass RAG pipeline)
            next_node = "simple_answer"
            logger.info(f"  ↳ Routing to: {next_node} (no retrieval needed)")
        else:
            # Route to router (full RAG pipeline)
            next_node = "router"
            logger.info(f"  ↳ Routing to: {next_node} (retrieval needed)")

        # Return Command with state updates + routing
        return Command(
            update={
                "query_type": result.query_type,
                "needs_retrieval": result.needs_retrieval,
                "pipeline_path": "simple" if result.query_type == "simple" else "complex",
            },
            goto=next_node,
        )

    except Exception as e:
        logger.error(
            f"Classification failed: {e}, defaulting to complex_standalone")
        # Default to complex path on error (safe fallback)
        return Command(
            update={
                "query_type": "complex_standalone",
                "needs_retrieval": True,
                "pipeline_path": "complex",
            },
            goto="router",
        )
