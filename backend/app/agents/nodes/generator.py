"""
LLM response generation node with streaming support.

This module synthesizes integration code from retrieved documentation chunks
using GPT-4, with support for token-by-token streaming.
"""

import re
import time

import tiktoken
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.agents.state import AgentState
from app.core.config import settings
from app.schemas.retrieval import SearchResult
from app.utils.logger import get_logger
from app.utils.observability import trace_node

logger = get_logger(__name__)

# LLM instance for generation
llm = ChatOpenAI(
    model=settings.openai_model,
    temperature=0.3,  # Lower temperature for more deterministic code generation
    api_key=settings.openai_api_key,
    streaming=True,  # Enable streaming
)

# System prompt for documentation assistance
SYSTEM_PROMPT = """You are a knowledgeable documentation assistant. Your task is to provide clear, accurate, and well-structured answers based **strictly** on the provided context.

Rules:
1. Answer the user's question using ONLY information from the provided context.
2. Cite sources using inline numbered markers [1], [2], etc. placed at the END of the sentence they support. Each number corresponds to the matching "Source N" in the context.
3. If the context does not contain enough information to fully answer the question, say so honestly rather than guessing or fabricating details.
4. Do NOT use external knowledge — only the retrieved documentation below.
5. Keep your tone professional, helpful, and neutral.
6. Structure your response with clear headings, numbered lists, or bullet points when it improves readability.
7. Do NOT include code examples unless the user explicitly asks for code.

Do not invent information. Do not hallucinate. Every factual claim must be grounded in a provided source."""


# User prompt template
USER_PROMPT_TEMPLATE = """Answer the following question using the retrieved documentation below.

QUESTION:
{query}

RETRIEVED DOCUMENTATION:
{context}

Provide a thorough answer with inline source citations [N] after each supported statement. If the documentation is insufficient, state what is missing."""


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
        # Prefer top-level document_title, fallback to metadata, then filename
        doc_title = getattr(chunk, "document_title", None)
        if not doc_title:
            doc_title = chunk.metadata.get(
                "document_title", chunk.metadata.get("filename", "Unknown Document")
            )

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
        logger.warning(f"Failed to count tokens with tiktoken: {e}, using word count approximation")
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
        logger.warning(f"Failed to count chat tokens: {e}, falling back to simple count")
        # Fallback: sum content tokens + conservative overhead
        return sum(count_tokens(msg.content, model) for msg in messages) + (len(messages) * 4) + 3


@trace_node("generator")
async def generator_node(state: AgentState) -> dict:
    """
    Generator node that synthesizes response from retrieved context.

    Process:
    1. Format retrieved chunks into context
    2. Build prompt with system + user messages
    3. Stream LLM response token-by-token (emitting tokens via custom stream)
    4. Track metadata (tokens, latency, cost)
    5. Return generated response

    Note: Uses llm.ainvoke(). When the graph runs with stream_mode="messages",
    LangGraph automatically emits AIMessageChunks through the messages stream,
    enabling token-by-token streaming without any manual writer loop.

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
    start_time = time.time()
    logger.info("⏱️  GENERATOR NODE: Starting LLM response generation")

    # Use the resolved retrieval_query (pronoun-resolved for follow-ups,
    # format-stripped for initial queries).  Fall back to original_query.
    query = state.get("retrieval_query") or state["original_query"]
    chunks = state.get("retrieved_chunks", [])

    if not chunks:
        logger.warning("No chunks retrieved, generating response without context")
        context = "No relevant documentation found. Please provide a general answer based on your knowledge."
    else:
        context = format_context(chunks)
        logger.info(f"Formatted context from {len(chunks)} chunks ({len(context)} chars)")

    # Build context-aware system prompt
    system_prompt_parts = [SYSTEM_PROMPT]

    # Add conversation summary if available
    conversation_summary = state.get("conversation_summary", "")
    if conversation_summary:
        system_prompt_parts.append(f"\n\nPrevious conversation context:\n{conversation_summary}")
        logger.info(
            f"Added conversation summary to system prompt ({len(conversation_summary)} chars)"
        )

    # Honour format/style instructions extracted by query_expander (e.g. "briefly", "in bullet points")
    format_instructions = state.get("format_instructions", "")
    if format_instructions:
        system_prompt_parts.append(
            f"\n\nFormatting instruction: {format_instructions}. "
            "You MUST honour this constraint in your response."
        )
        logger.info(f"Applied format instructions: '{format_instructions}'")

    system_prompt = "\n".join(system_prompt_parts)

    # Build messages
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=USER_PROMPT_TEMPLATE.format(query=query, context=context)),
    ]

    logger.info("Calling LLM for response generation")

    try:
        # Invoke LLM — when graph runs with stream_mode="messages", LangGraph
        # automatically intercepts ainvoke() and streams AIMessageChunks through
        # the messages stream without any manual writer/astream loop needed.
        llm_start = time.time()

        response = await llm.ainvoke(messages)
        full_response = response.content

        llm_time = time.time() - llm_start
        logger.info(f"  ↳ LLM generation took {llm_time:.3f}s")

        # Calculate accurate token counts using tiktoken after streaming completes
        # Use chat-aware token counting to account for ChatML formatting overhead
        prompt_tokens = count_chat_tokens(messages, model=settings.openai_model)

        # Compute completion tokens (generated response)
        completion_tokens = count_tokens(full_response, model=settings.openai_model)
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
        estimated_cost = (prompt_tokens * 0.00003) + (completion_tokens * 0.00006)

        # Build citation_map only for markers the LLM actually referenced.
        # Scan the response for [N] patterns and include only those entries.
        referenced_markers = {int(m) for m in re.findall(r"\[(\d+)\]", full_response)}

        # Re-number citations to be sequential ([1],[5],[10] → [1],[2],[3]).
        # Build a mapping from the original chunk index to a new sequential index.
        sorted_markers = sorted(referenced_markers)
        remap: dict[int, int] = {old: new for new, old in enumerate(sorted_markers, 1)}

        if remap:

            def _renumber(match: re.Match) -> str:
                original = int(match.group(1))
                return f"[{remap.get(original, original)}]"

            full_response = re.sub(r"\[(\d+)\]", _renumber, full_response)
            logger.info(
                f"Re-numbered citations: {sorted_markers} → {[remap[m] for m in sorted_markers]}"
            )

        citation_map: dict[int, dict] = {}
        citations = []
        for idx, chunk in enumerate(chunks, 1):
            if idx in referenced_markers:
                new_idx = remap.get(idx, idx)
                citation_map[new_idx] = {
                    "chunk_id": str(chunk.chunk_id),
                    "document_id": str(chunk.document_id),
                    "document_title": chunk.document_title,
                    "content": chunk.content[:300],
                    "score": chunk.score,
                    "source": chunk.source,
                }
                citations.append(
                    {
                        "index": new_idx,
                        "chunk_id": str(chunk.chunk_id),
                        "document_id": str(chunk.document_id),
                        "document_title": chunk.document_title,
                        "content": chunk.content,
                        "preview": chunk.content[:200],
                        "score": chunk.score,
                        "original_score": chunk.original_score,
                        "source": chunk.source,
                    }
                )

        logger.info(
            f"LLM referenced markers {sorted_markers} → remapped to {sorted(citation_map.keys())}, "
            f"citation_map has {len(citation_map)} of {len(chunks)} chunks"
        )

        logger.info(
            f"Built {len(citations)} citations and {len(citation_map)} citation_map entries"
        )

        # Return state update.
        # NOTE: We do NOT add an AIMessage to messages here. The validator
        # will create the AIMessage only when the response is approved. This
        # prevents duplicate AI messages in the checkpoint on validator retries.
        return {
            "generated_response": full_response,
            "citation_map": {str(k): v for k, v in citation_map.items()},
            "citations": citations,
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
            },
        }

    except Exception as e:
        logger.error(f"Generation failed: {e}", exc_info=True)

        # Return error response — no AIMessage here, validator will persist it.
        error_msg = "I encountered an error while generating the response. Please try again."
        return {
            "generated_response": error_msg,
            "citation_map": {},
            "citations": [],
            "metadata": {
                "generation": {
                    "error": str(e),
                    "chunks_used": len(chunks),
                }
            },
        }
