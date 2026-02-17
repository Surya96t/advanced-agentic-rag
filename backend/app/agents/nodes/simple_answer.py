"""
Simple answer node for handling queries without retrieval.

This node handles simple queries like greetings, thanks, and meta questions
using only conversation context, without triggering the RAG pipeline.
"""

from typing import Any

from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from langgraph.config import get_stream_writer

from app.agents.state import AgentState
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def generate_simple_answer(state: AgentState) -> dict[str, Any]:
    """
    Generate answer for simple queries without retrieval.

    Uses conversation context only. Suitable for:
    - Greetings: "hi", "hello"
    - Thanks: "thank you", "thanks"
    - Meta questions: "what can you help with?"
    - Simple follow-ups: "yes", "no", "ok"

    Args:
        state: Current agent state with messages (conversation history)

    Returns:
        State update dict with generated_response and messages

    Example:
        >>> state = {
        ...     "messages": [HumanMessage(content="Hello!")],
        ...     "query": "Hello!"
        ... }
        >>> result = await generate_simple_answer(state)
        >>> "generated_response" in result
        True
    """
    logger.info("💬 SIMPLE ANSWER NODE: Generating response without retrieval")

    messages = state.get("messages", [])
    query = state.get("query", state.get("original_query", ""))

    # Use LLM with conversation context
    llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=0.7,
        api_key=settings.openai_api_key,
    )

    # Simple system prompt for conversational responses
    system_msg = """You are a helpful documentation assistant. Respond naturally to the user.

For greetings, be friendly and brief.
For questions about your capabilities, explain you can answer questions about technical documentation using RAG.
For follow-up questions, use the conversation context to provide helpful responses.
For thanks, acknowledge graciously and offer further help.

Keep responses concise, professional, and helpful."""

    # Build message list for LLM
    llm_messages = [{"role": "system", "content": system_msg}]

    # Add conversation history with explicit type mapping
    for msg in messages:
        # Validate message has required attributes
        if not hasattr(msg, "type"):
            logger.warning(
                "Message missing 'type' attribute, skipping",
                extra={"message": str(msg)[:100]}
            )
            continue

        if not hasattr(msg, "content"):
            logger.warning(
                "Message missing 'content' attribute, skipping",
                extra={"message_type": msg.type}
            )
            continue

        # Explicit type mapping for known message types
        msg_type = msg.type
        if msg_type == "human":
            role = "user"
        elif msg_type in ("ai", "assistant"):
            role = "assistant"
        elif msg_type == "system":
            role = "system"
        elif msg_type == "tool":
            role = "tool"
        else:
            # Unknown message type - log warning and skip
            logger.warning(
                f"Unknown message type '{msg_type}', skipping message",
                extra={"message_type": msg_type, "content_preview": str(msg.content)[
                    :50]}
            )
            continue

        llm_messages.append({"role": role, "content": msg.content})

    logger.info(f"Generating simple response for: '{query[:50]}...'")

    try:
        # Get stream writer for emitting custom token events
        writer = None
        try:
            writer = get_stream_writer()
        except Exception:
            # No stream writer available (not in streaming mode)
            pass

        # Stream response from LLM token-by-token
        full_response = ""

        async for chunk in llm.astream(llm_messages):
            if chunk.content:
                token = chunk.content
                full_response += token

                # Emit token event for real-time streaming (if writer available)
                if writer:
                    writer({
                        "type": "token",
                        "token": token,
                        "model": settings.openai_model,
                    })

        logger.info(
            f"  ↳ Generated simple response ({len(full_response)} chars)")

        return {
            "messages": [AIMessage(content=full_response)],
            "generated_response": full_response,
        }

    except Exception as e:
        logger.error(f"Simple answer generation failed: {e}", exc_info=True)

        # Fallback response
        fallback = "Hello! I'm here to help you with technical documentation. What would you like to know?"

        return {
            "messages": [AIMessage(content=fallback)],
            "generated_response": fallback,
        }
