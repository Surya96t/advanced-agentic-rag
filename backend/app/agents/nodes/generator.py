"""
LLM response generation node with streaming support.

This module synthesizes integration code from retrieved documentation chunks
using GPT-4, with support for token-by-token streaming.
"""

import time

from langchain_core.messages import HumanMessage, SystemMessage
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


async def generator_node(state: AgentState) -> dict:
    """
    Generator node that synthesizes response from retrieved context.

    Process:
    1. Format retrieved chunks into context
    2. Build prompt with system + user messages
    3. Stream LLM response token-by-token
    4. Track metadata (tokens, latency, cost)
    5. Return generated response

    Note: Streaming is handled by LangGraph's streaming modes.
    This node just uses the streaming LLM, and tokens are automatically
    streamed if graph is invoked with stream_mode="messages".

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
    logger.info("Generator node: Synthesizing response from retrieved context")

    start_time = time.time()

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

    # Build messages
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=USER_PROMPT_TEMPLATE.format(
            query=query,
            context=context
        ))
    ]

    logger.info("Calling LLM for response generation")

    try:
        # Stream the response
        # Note: LangGraph automatically handles streaming when stream_mode="messages"
        # We just collect the full response here
        full_response = ""
        token_count = 0

        async for chunk in llm.astream(messages):
            if chunk.content:
                full_response += chunk.content
                token_count += 1

        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)

        logger.info(
            "Generation complete",
            tokens=token_count,
            latency_ms=latency_ms,
            response_length=len(full_response)
        )

        # Estimate cost (rough approximation)
        # GPT-4: ~$0.03/1K prompt tokens, ~$0.06/1K completion tokens
        # This is a rough estimate; actual costs depend on model pricing
        prompt_tokens = len(SYSTEM_PROMPT.split()) + \
            len(query.split()) + len(context.split())
        completion_tokens = token_count
        estimated_cost = (prompt_tokens * 0.00003) + \
            (completion_tokens * 0.00006)

        # Return state update
        return {
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

        # Return error response
        return {
            "generated_response": f"I encountered an error while generating the response: {str(e)}. Please try again.",
            "metadata": {
                "generation": {
                    "error": str(e),
                    "chunks_used": len(chunks),
                }
            }
        }
