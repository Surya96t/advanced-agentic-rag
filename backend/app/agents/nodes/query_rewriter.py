"""
Query rewriter node for conversational follow-up queries.

When a user asks a vague follow-up like "can you explain it in more detail?",
this node rewrites the query to be self-contained by resolving pronouns and
implicit references using the conversation history.

Example:
    User: "What is the transportation service agreement about?"
    AI:   "The TSA covers ... [details] ..."
    User: "can you explain it in more detail?"
                ↓ query_rewriter
    retrieval_query: "can you explain the transportation service agreement in more detail?"
"""

import time

from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

from app.agents.state import AgentState
from app.core.config import settings
from app.utils.logger import get_logger
from app.utils.observability import trace_node

logger = get_logger(__name__)

# LLM for rewriting — low temperature for deterministic resolution
_rewriter_llm = ChatOpenAI(
    model=settings.openai_model,
    temperature=0.0,
    api_key=settings.openai_api_key,
)

REWRITE_PROMPT = """You are a query rewriting assistant. The user asked a follow-up question \
that may contain vague references (pronouns like "it", "that", "this", or implicit subjects).

Rewrite the CURRENT QUERY to be fully self-contained by resolving all vague references \
using the conversation history below. Keep the intent and wording as close to the original \
as possible — only substitute the vague references with their specific referents.

If the current query is already self-contained (no vague references), return it unchanged.

CONVERSATION HISTORY (most recent last):
{history}

CURRENT QUERY: {query}

REWRITTEN QUERY (self-contained, no unresolved pronouns):"""


def _format_recent_turns(messages: list, max_turns: int = 4) -> str:
    """
    Format the last ``max_turns`` conversation turns into a readable string.

    Skips the final message (which is the current query) and truncates long
    AI responses so the prompt doesn't exceed the context limit.

    Args:
        messages: Full message list from state (includes the current HumanMessage).
        max_turns: Maximum number of prior turns to include.

    Returns:
        Formatted string of prior conversation.
    """
    # Exclude the current (last) HumanMessage — that's the query being rewritten.
    prior = messages[:-1] if messages else []

    # Take only the most recent max_turns messages from the prior history.
    prior = prior[-max_turns * 2:]  # *2 because each turn is 2 messages (human + AI)

    lines = []
    for msg in prior:
        if isinstance(msg, HumanMessage):
            lines.append(f"User: {msg.content}")
        elif isinstance(msg, AIMessage):
            # Truncate long AI responses to keep the prompt concise.
            content = msg.content[:400] + "..." if len(msg.content) > 400 else msg.content
            lines.append(f"Assistant: {content}")

    return "\n".join(lines) if lines else "No prior conversation."


@trace_node("query_rewriter")
async def query_rewriter_node(state: AgentState) -> dict:
    """
    Rewrite vague follow-up queries to be self-contained using conversation context.

    Reads ``original_query``, ``messages``, and ``conversation_summary`` from state.
    Writes the resolved query to ``retrieval_query`` so it flows into the
    existing router → query_expander → retriever pipeline unchanged.

    ``original_query`` is never modified — it must stay as the user's raw input
    for the generator and validator to use.

    Guards:
    - If there is no prior conversation (≤ 1 message), skip rewriting.
    - If the LLM call fails, fall back to the original query (no crash).

    Args:
        state: Current agent state.

    Returns:
        Dict with updated ``retrieval_query``.
    """
    start_time = time.time()
    original_query = state.get("original_query", "")
    messages = state.get("messages", [])
    conversation_summary = state.get("conversation_summary", "")

    logger.info(
        f"⏱️  QUERY_REWRITER NODE: Starting | "
        f"query='{original_query[:80]}' | "
        f"messages={len(messages)}"
    )

    # Guard: if there is no prior context there is nothing to resolve.
    # ≤ 1 means only the current HumanMessage exists (first turn).
    if len(messages) <= 1:
        logger.info(
            "  ↳ No prior context — skipping rewrite, passing original query through"
        )
        return {"retrieval_query": original_query}

    # Build conversation history string for the prompt.
    history_str = _format_recent_turns(messages, max_turns=4)

    # Prepend summary if available (covers older turns that were trimmed).
    if conversation_summary:
        history_str = f"[Earlier conversation summary: {conversation_summary}]\n\n{history_str}"

    prompt = REWRITE_PROMPT.format(history=history_str, query=original_query)

    try:
        response = await _rewriter_llm.ainvoke(prompt)
        rewritten = response.content.strip()

        # Sanity check: if the LLM returned something empty or very short, fall back.
        if not rewritten or len(rewritten) < 5:
            logger.warning(
                "  ↳ Rewriter returned empty/short response — falling back to original"
            )
            return {"retrieval_query": original_query}

        elapsed = time.time() - start_time
        logger.info(
            f"⏱️  QUERY_REWRITER NODE: Completed in {elapsed:.3f}s | "
            f"original='{original_query[:60]}' | "
            f"rewritten='{rewritten[:60]}'"
        )

        return {"retrieval_query": rewritten}

    except Exception as e:
        logger.error(
            f"Query rewriting failed: {e} — falling back to original query",
            exc_info=True,
        )
        return {"retrieval_query": original_query}
