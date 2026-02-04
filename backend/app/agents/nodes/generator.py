"""
LLM response generation node with streaming support.

This module synthesizes integration code from retrieved documentation chunks
using GPT-4, with support for token-by-token streaming.
"""

import time

import tiktoken
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.agents.state import AgentState
from app.core.config import settings
from app.schemas.retrieval import SearchResult
from app.utils.logger import get_logger

logger = get_logger(__name__)

# LLM instance for generation
llm = ChatOpenAI(
    model=settings.openai_model,
    temperature=0.3,  # Lower temperature for more deterministic code generation
    api_key=settings.openai_api_key,
    streaming=True,  # Enable streaming
)

# System prompt for integration code synthesis
SYSTEM_PROMPT = """You are an expert integration developer helping developers combine different tools and frameworks.

Your role is to:
- Provide complete, working code examples
- Cite sources using [Source: Document Title] format
- Explain setup steps clearly and in order
- Include error handling and edge cases
- Mention version compatibility when relevant
- Use TypeScript for frontend code, Python for backend (unless specified otherwise)

Format your response as:
1. Brief explanation of the solution
2. Step-by-step setup instructions
3. Complete code examples with comments
4. Testing/verification steps

Always be specific, accurate, and cite your sources."""


# User prompt template
USER_PROMPT_TEMPLATE = """Answer this question using the provided documentation:

QUESTION:
{query}

DOCUMENTATION:
{context}

Provide a complete, working solution with proper code examples and source citations."""


def format_context(chunks: list[SearchResult]) -> str:
    """
    Format retrieved chunks into context string for LLM.

    Args:
        chunks: Retrieved and re-ranked search results

    Returns:
        Formatted context string with source attribution

    Example:
        >>> chunks = [SearchResult(...), SearchResult(...)]
        >>> context = format_context(chunks)
        >>> "Source 1: Clerk Guide\\n\\nContent..." in context
        True
    """
    if not chunks:
        return "No relevant documentation found."

    context_parts = []
    for idx, chunk in enumerate(chunks, 1):
        doc_title = chunk.metadata.get("document_title", "Unknown Document")
        content = chunk.content.strip()
        score = chunk.score

        # Format each chunk with clear separation
        context_parts.append(
            f"--- Source {idx}: {doc_title} (Relevance: {score:.2f}) ---\n{content}\n"
        )

    return "\n".join(context_parts)


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Count tokens in text using tiktoken.

    Args:
        text: Text to count tokens for
        model: Model name to get the correct encoding

    Returns:
        Number of tokens

    Example:
        >>> count_tokens("Hello world")
        2
    """
    try:
        # Get the encoding for the model
        # For gpt-4 and gpt-3.5-turbo models, use cl100k_base encoding
        if "gpt-4" in model or "gpt-3.5" in model:
            encoding = tiktoken.get_encoding("cl100k_base")
        else:
            # Fallback to cl100k_base for unknown models
            encoding = tiktoken.get_encoding("cl100k_base")

        return len(encoding.encode(text))
    except Exception as e:
        logger.warning(
            f"Failed to count tokens with tiktoken: {e}, using word count approximation"
        )
        # Fallback: rough approximation (1 token ≈ 0.75 words)
        return int(len(text.split()) * 1.33)


def count_chat_tokens(messages: list, model: str = "gpt-4") -> int:
    """
    Count tokens for chat messages including ChatML formatting overhead.

    ChatML format adds extra tokens for role tags and message structure:
    - Each message adds ~4 tokens for formatting (<|im_start|>role, <|im_end|>)
    - Total overhead = num_messages * 4 + 3 (for prompt priming)

    Args:
        messages: List of message objects (SystemMessage, HumanMessage, etc.)
        model: Model name to get the correct encoding

    Returns:
        Total token count including ChatML overhead

    Example:
        >>> messages = [SystemMessage(content="You are helpful"), HumanMessage(content="Hi")]
        >>> count_chat_tokens(messages)
        15  # content tokens + ChatML overhead
    """
    try:
        total_tokens = 0

        # Count tokens for each message content
        for message in messages:
            # Add content tokens
            total_tokens += count_tokens(message.content, model)
            # Add per-message ChatML overhead (~4 tokens per message)
            # Format: <|im_start|>role\ncontent<|im_end|>
            total_tokens += 4

        # Add tokens for prompt priming (varies by model, use conservative estimate)
        total_tokens += 3

        return total_tokens
    except Exception as e:
        logger.warning(
            f"Failed to count chat tokens: {e}, falling back to simple count")
        # Fallback: sum content tokens + conservative overhead
        return sum(count_tokens(msg.content, model) for msg in messages) + (len(messages) * 4) + 3


async def generator_node(state: AgentState) -> dict:
    """
    Generator node that synthesizes response from retrieved context.

    Process:
    1. Format retrieved chunks into context
    2. Build prompt with system + user messages
    3. Stream LLM response token-by-token (emitting tokens via custom stream)
    4. Track metadata (tokens, latency, cost)
    5. Return generated response

    Note: When used with stream_mode="custom" or ["updates", "custom"], this node
    emits custom token events for real-time token-by-token streaming. When used with
    ainvoke() or without custom streaming, it returns the full response synchronously.

    Args:
        state: Current agent state with retrieved_chunks and original_query

    Returns:
        State update dict with generated_response and metadata

    Example:
        >>> state = {
        ...     "original_query": "How to integrate Clerk?",
        ...     "retrieved_chunks": [chunk1, chunk2]
        ... }
        >>> result = await generator_node(state)
        >>> "generated_response" in result
        True
    """
    from langgraph.config import get_stream_writer

    start_time = time.time()
    logger.info("⏱️  GENERATOR NODE: Starting LLM response generation")

    # Get query and chunks
    query = state["original_query"]
    chunks = state.get("retrieved_chunks", [])

    if not chunks:
        logger.warning(
            "No chunks retrieved, generating response without context")
        context = "No relevant documentation found. Please provide a general answer based on your knowledge."
    else:
        context = format_context(chunks)
        logger.info(
            f"Formatted context from {len(chunks)} chunks ({len(context)} chars)")

    # Build context-aware system prompt
    system_prompt_parts = [SYSTEM_PROMPT]

    # Add conversation summary if available
    conversation_summary = state.get("conversation_summary", "")
    if conversation_summary:
        system_prompt_parts.append(
            f"\n\nPrevious conversation context:\n{conversation_summary}"
        )
        logger.info(
            f"Added conversation summary to system prompt ({len(conversation_summary)} chars)")

    system_prompt = "\n".join(system_prompt_parts)

    # Build messages
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=USER_PROMPT_TEMPLATE.format(
            query=query,
            context=context
        ))
    ]

    logger.info("Calling LLM for response generation")

    try:
        # Get stream writer for emitting custom token events
        # This will only work if stream_mode="custom" is enabled
        writer = None
        try:
            writer = get_stream_writer()
        except Exception:
            # No stream writer available (e.g., not in streaming mode)
            pass

        # Stream the response token-by-token
        llm_start = time.time()
        full_response = ""

        # Stream tokens from LLM
        async for chunk in llm.astream(messages):
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

        llm_time = time.time() - llm_start
        logger.info(f"  ↳ LLM generation took {llm_time:.3f}s")

        # Calculate accurate token counts using tiktoken after streaming completes
        # Use chat-aware token counting to account for ChatML formatting overhead
        prompt_tokens = count_chat_tokens(
            messages, model=settings.openai_model)

        # Compute completion tokens (generated response)
        completion_tokens = count_tokens(
            full_response, model=settings.openai_model)
        total_tokens = prompt_tokens + completion_tokens

        end_time = time.time()
        elapsed_time = end_time - start_time
        latency_ms = int(elapsed_time * 1000)

        logger.info(
            f"⏱️  GENERATOR NODE: Completed in {elapsed_time:.3f}s | "
            f"Tokens: {total_tokens} ({prompt_tokens} prompt + {completion_tokens} completion)"
        )

        # Calculate cost based on actual token counts
        # GPT-4: ~$0.03/1K prompt tokens, ~$0.06/1K completion tokens
        # Adjust these rates based on your actual model pricing
        estimated_cost = (prompt_tokens * 0.00003) + \
            (completion_tokens * 0.00006)

        # Return state update (MUST include messages to persist to conversation history!)
        return {
            "messages": [AIMessage(content=full_response)],
            "generated_response": full_response,
            "metadata": {
                "generation": {
                    "model": settings.openai_model,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                    "latency_ms": latency_ms,
                    "estimated_cost_usd": round(estimated_cost, 6),
                    "chunks_used": len(chunks),
                }
            }
        }

    except Exception as e:
        logger.error(f"Generation failed: {e}", exc_info=True)

        # Return error response (still need to add to messages!)
        error_msg = f"I encountered an error while generating the response. Please try again."
        return {
            "messages": [AIMessage(content=error_msg)],
            "generated_response": error_msg,
            "metadata": {
                "generation": {
                    "error": str(e),
                    "chunks_used": len(chunks),
                }
            }
        }
