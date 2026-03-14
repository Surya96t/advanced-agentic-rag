"""
Conversation summarization utilities for managing long conversation histories.

This module provides LLM-based summarization to condense older messages
while preserving essential context.
"""

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI

from app.core.config import settings


class ConversationSummarizer:
    """Create summaries of conversation history."""

    def __init__(self):
        """Initialize conversation summarizer with LLM."""
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0,
            api_key=settings.openai_api_key,
        )

    async def summarize_messages(
        self, messages: list[BaseMessage], max_summary_length: int = 500
    ) -> str:
        """
        Summarize a list of messages.

        Returns concise summary focusing on:
        - Topics discussed
        - Key information shared
        - User goals/intent

        Args:
            messages: Messages to summarize
            max_summary_length: Maximum length of summary in characters

        Returns:
            Summary string (truncated to max_summary_length)

        Example:
            >>> summarizer = ConversationSummarizer()
            >>> messages = [
            ...     HumanMessage(content="How do I use Prisma?"),
            ...     AIMessage(content="Prisma is an ORM..."),
            ... ]
            >>> summary = await summarizer.summarize_messages(messages)
            >>> len(summary) <= 500
            True
        """
        if not messages:
            return ""

        # Format messages
        conversation = self._format_for_summary(messages)

        prompt = f"""Summarize this conversation concisely (max {max_summary_length} chars).
Focus on:
1. Main topics discussed
2. Key technical details or solutions provided
3. User's goals or questions

Conversation:
{conversation}

Summary:"""

        response = await self.llm.ainvoke([HumanMessage(content=prompt)])

        content = response.content if isinstance(response.content, str) else ""
        summary = content[:max_summary_length]
        return summary

    def _format_for_summary(self, messages: list[BaseMessage]) -> str:
        """
        Format messages as text for summarization.

        Args:
            messages: Messages to format

        Returns:
            Formatted conversation string
        """
        lines = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                lines.append(f"User: {msg.content}")
            elif isinstance(msg, AIMessage):
                # Exclude tool calls, keep only text
                content = msg.content if isinstance(msg.content, str) else ""
                if content:
                    lines.append(f"Assistant: {content}")
        return "\n".join(lines)

    async def progressive_summarization(
        self, messages: list[BaseMessage], chunk_size: int = 20
    ) -> str:
        """
        Summarize long conversations progressively.

        For very long histories (100+ messages):
        1. Split into chunks
        2. Summarize each chunk
        3. Summarize the summaries

        Args:
            messages: Full message history
            chunk_size: Size of each chunk to summarize

        Returns:
            Final condensed summary

        Example:
            >>> summarizer = ConversationSummarizer()
            >>> long_messages = [...]  # 150 messages
            >>> summary = await summarizer.progressive_summarization(long_messages)
            >>> len(summary) < len(str(long_messages))
            True
        """
        if len(messages) <= chunk_size:
            return await self.summarize_messages(messages)

        # Split into chunks
        chunks = [messages[i : i + chunk_size] for i in range(0, len(messages), chunk_size)]

        # Summarize each chunk
        chunk_summaries = []
        for chunk in chunks:
            summary = await self.summarize_messages(chunk, max_summary_length=200)
            chunk_summaries.append(summary)

        # Summarize the summaries
        final_prompt = f"""Combine these conversation summaries into one concise summary:

{chr(10).join(f"{i + 1}. {s}" for i, s in enumerate(chunk_summaries))}

Final summary:"""
        response = await self.llm.ainvoke([HumanMessage(content=final_prompt)])
        content = response.content if isinstance(response.content, str) else ""
        return content[:500]  # Apply consistent max length
        return response.content
