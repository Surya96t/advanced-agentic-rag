"""
Conversation context loader node for managing message history.

This node loads conversation history from the checkpointer, counts tokens,
and trims/summarizes messages if they exceed the configured limit.
"""

from typing import Any

from langchain_core.messages import SystemMessage

from app.agents.state import AgentState
from app.core.config import settings
from app.utils.conversation_summarizer import ConversationSummarizer
from app.utils.logger import get_logger
from app.utils.message_trimmer import MessageTrimmer
from app.utils.token_counter import TokenCounter

logger = get_logger(__name__)


async def load_conversation_context(state: AgentState) -> dict[str, Any]:
    """
    Load and manage conversation context with trimming and summarization.

    Uses advanced context management strategies:
    1. Count tokens with TokenCounter
    2. Try simple trimming first
    3. If still over limit, trim + summarize older messages
    4. Preserve system messages and recent context always

    Args:
        state: Current agent state with message history

    Returns:
        Updated state with trimmed messages and context summary
    """
    messages = list(state.get("messages", []))

    logger.info(f"📚 CONTEXT LOADER: Managing {len(messages)} messages")

    # Initialize utilities
    counter = TokenCounter(model=settings.openai_model)
    trimmer = MessageTrimmer(counter)
    summarizer = ConversationSummarizer()

    # Count current tokens
    current_tokens = counter.count_messages_tokens(messages)

    logger.info(
        f"  ↳ Current token count: {current_tokens}/{settings.max_conversation_tokens}")

    # If under limit, return as-is
    if current_tokens <= settings.max_conversation_tokens:
        logger.info("  ↳ Within limit, no trimming needed")
        return {
            "messages": messages,
            "context_window_tokens": current_tokens,
            "conversation_summary": "",
            "messages_summarized": 0,
        }

    logger.info("  ↳ Over limit, applying context management")

    # Strategy 1: Try simple trimming first
    trimmed = trimmer.trim_to_token_limit(
        messages,
        max_tokens=settings.max_conversation_tokens,
        keep_recent=settings.recent_message_count,
    )

    trimmed_tokens = counter.count_messages_tokens(trimmed)

    # If trimming is enough, use it
    if trimmed_tokens <= settings.max_conversation_tokens:
        logger.info(
            f"  ↳ Trimmed to {len(trimmed)} messages ({trimmed_tokens} tokens)"
        )
        return {
            "messages": trimmed,
            "context_window_tokens": trimmed_tokens,
            "conversation_summary": "",
            "messages_summarized": 0,
        }

    # Strategy 2: Trim + summarize older messages
    logger.info("  ↳ Trimming alone insufficient, adding summarization")

    system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
    other_msgs = [m for m in messages if not isinstance(m, SystemMessage)]

    # Keep last N messages
    recent = other_msgs[-settings.recent_message_count:]
    older = other_msgs[: -settings.recent_message_count]

    # Summarize older messages
    if older:
        logger.info(f"  ↳ Summarizing {len(older)} older messages")
        summary = await summarizer.summarize_messages(older)
        summary_msg = SystemMessage(
            content=f"Previous conversation summary:\n{summary}"
        )

        reconstructed = system_msgs + [summary_msg] + recent
        reconstructed_tokens = counter.count_messages_tokens(reconstructed)

        logger.info(
            f"  ↳ Reconstructed: {len(reconstructed)} messages ({reconstructed_tokens} tokens)"
        )

        return {
            "messages": reconstructed,
            "conversation_summary": summary,
            "context_window_tokens": reconstructed_tokens,
            "messages_summarized": len(older),
        }

    # Fallback: Just use recent messages
    logger.info("  ↳ Fallback: using recent messages only")
    fallback = system_msgs + recent
    fallback_tokens = counter.count_messages_tokens(fallback)

    return {
        "messages": fallback,
        "context_window_tokens": fallback_tokens,
        "conversation_summary": "Older messages truncated",
        "messages_summarized": len(older) if older else 0,
    }
