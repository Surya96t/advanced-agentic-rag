"""
Query classifier node for determining routing strategy.

This node uses an LLM with structured output to classify queries as:
- simple: Greetings, thanks, meta questions (no retrieval needed)
- conversational_followup: References previous messages (minimal retrieval)
- complex_standalone: Technical questions requiring full RAG pipeline
"""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.types import Command
from pydantic import BaseModel, Field

from app.agents.state import AgentState
from app.core.config import settings
from app.utils.logger import get_logger
from app.utils.observability import trace_node

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


@trace_node("classifier")
async def classify_query(state: AgentState) -> Command:
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
        Command object with state updates (query_type, needs_retrieval, pipeline_path)
        and routing decision (goto: "simple_answer" or "router")

    Example:
        >>> state = {"query": "hi", "messages": []}
        >>> result = await classify_query(state)
        >>> result.goto
        'simple_answer'
        >>> result.update["query_type"]
        'simple'
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

    classification_prompt = f"""Classify this user query to determine the best handling strategy.

---
CATEGORY DEFINITIONS & EXAMPLES

simple — Greetings, thanks, chitchat, meta questions. No retrieval needed.
  Q: "hi there"                       → simple, needs_retrieval=false
  Q: "hello!"                         → simple, needs_retrieval=false
  Q: "thanks, that helped"            → simple, needs_retrieval=false
  Q: "great, thanks!"                 → simple, needs_retrieval=false
  Q: "what can you help me with?"     → simple, needs_retrieval=false
  Q: "are you an AI?"                 → simple, needs_retrieval=false

conversational_followup — Refers to or continues the prior turn. Retrieval depends on whether new info is needed.
  Q: "tell me more about that"        → conversational_followup, needs_retrieval=true
  Q: "can you give an example?"       → conversational_followup, needs_retrieval=true
  Q: "what about the exceptions?"     → conversational_followup, needs_retrieval=true
  Q: "how does that compare to X?"    → conversational_followup, needs_retrieval=true
  Q: "can you go deeper on point 2?"  → conversational_followup, needs_retrieval=true
  Q: "ok, so what would happen if…"   → conversational_followup, needs_retrieval=false

complex_standalone — Self-contained question requiring full document lookup.
  Q: "what are the key terms in the transportation agreement?"  → complex_standalone, needs_retrieval=true
  Q: "summarize the termination clauses"                        → complex_standalone, needs_retrieval=true
  Q: "what obligations does the shipper have?"                  → complex_standalone, needs_retrieval=true
  Q: "explain the payment schedule in the contract"             → complex_standalone, needs_retrieval=true
  Q: "what are the main findings in the report?"                → complex_standalone, needs_retrieval=true
  Q: "how does the author define retrieval augmented generation?" → complex_standalone, needs_retrieval=true

---
CONVERSATION CONTEXT (last few turns):
{context_str}

CURRENT QUERY TO CLASSIFY:
{query}

Respond with a QueryClassification object."""

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
            pipeline_path = "simple"
            logger.info(f"  ↳ Routing to: {next_node} (no retrieval needed)")
        elif result.query_type == "conversational_followup" and result.needs_retrieval:
            # Vague follow-up needs pronoun resolution before retrieval
            next_node = "query_rewriter"
            pipeline_path = "complex"
            logger.info(f"  ↳ Routing to: {next_node} (follow-up needs context-aware rewrite)")
        else:
            # complex_standalone — route directly to router (full RAG pipeline)
            next_node = "router"
            pipeline_path = "complex"
            logger.info(f"  ↳ Routing to: {next_node} (retrieval needed)")

        # Return Command with state updates + routing
        # Note: pipeline_path mirrors the routing decision for consistency
        return Command(
            update={
                "query_type": result.query_type,
                "needs_retrieval": result.needs_retrieval,
                "pipeline_path": pipeline_path,
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
