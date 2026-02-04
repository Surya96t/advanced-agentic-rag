"""
Token counting utilities for managing conversation context windows.

This module provides accurate token counting using tiktoken for OpenAI models,
essential for managing context window limits in conversational agents.
"""

import tiktoken
from langchain_core.messages import BaseMessage


class TokenCounter:
    """Utility for counting tokens in messages and text."""

    def __init__(self, model: str = "gpt-4"):
        """
        Initialize token counter with model-specific encoding.

        Args:
            model: Model name (e.g., "gpt-4", "gpt-3.5-turbo")
        """
        self.model = model
        self.encoding = tiktoken.encoding_for_model(model)

    def count_message_tokens(self, message: BaseMessage) -> int:
        """
        Count tokens in a single message.

        Includes overhead for ChatML formatting:
        - Message role and formatting adds ~4 tokens
        - Content is tokenized with model-specific encoding

        Args:
            message: LangChain message object

        Returns:
            Number of tokens including formatting overhead

        Example:
            >>> counter = TokenCounter("gpt-4")
            >>> msg = HumanMessage(content="Hello world")
            >>> counter.count_message_tokens(msg)
            6  # "Hello world" (2 tokens) + formatting (4 tokens)
        """
        # Count message content
        tokens = len(self.encoding.encode(message.content))

        # Add overhead for message formatting (role, etc.)
        # ChatML format: <|im_start|>role\ncontent<|im_end|>
        tokens += 4  # Approximate overhead per message

        return tokens

    def count_messages_tokens(self, messages: list[BaseMessage]) -> int:
        """
        Count total tokens in message list.

        Args:
            messages: List of LangChain message objects

        Returns:
            Total token count for all messages

        Example:
            >>> counter = TokenCounter("gpt-4")
            >>> messages = [
            ...     HumanMessage(content="Hi"),
            ...     AIMessage(content="Hello! How can I help?")
            ... ]
            >>> counter.count_messages_tokens(messages)
            15  # Total including formatting
        """
        return sum(self.count_message_tokens(msg) for msg in messages)

    def count_text_tokens(self, text: str) -> int:
        """
        Count tokens in raw text.

        Args:
            text: Text string to count

        Returns:
            Number of tokens

        Example:
            >>> counter = TokenCounter("gpt-4")
            >>> counter.count_text_tokens("Hello world")
            2
        """
        return len(self.encoding.encode(text))

    def estimate_context_usage(
        self,
        messages: list[BaseMessage],
        system_prompt: str = "",
        retrieved_docs: str = "",
    ) -> dict:
        """
        Estimate total context window usage.

        Breaks down token usage by component:
        - Message history
        - System prompt
        - Retrieved documents
        - Total and remaining tokens

        Args:
            messages: Conversation message history
            system_prompt: System prompt text
            retrieved_docs: Retrieved document context

        Returns:
            Dictionary with token breakdown and remaining tokens

        Example:
            >>> counter = TokenCounter("gpt-4")
            >>> usage = counter.estimate_context_usage(
            ...     messages=[HumanMessage(content="Hi")],
            ...     system_prompt="You are helpful",
            ...     retrieved_docs="Doc content here"
            ... )
            >>> usage.keys()
            dict_keys(['messages', 'system', 'documents', 'total', 'remaining'])
        """
        msg_tokens = self.count_messages_tokens(messages)
        sys_tokens = self.count_text_tokens(system_prompt)
        doc_tokens = self.count_text_tokens(retrieved_docs)

        total = msg_tokens + sys_tokens + doc_tokens

        # Assume 8K context window (adjust based on actual model)
        # gpt-4: 8K, gpt-4-32k: 32K, gpt-4-turbo: 128K
        max_tokens = 8000
        if "32k" in self.model:
            max_tokens = 32000
        elif "turbo" in self.model or "gpt-4o" in self.model:
            max_tokens = 128000

        return {
            "messages": msg_tokens,
            "system": sys_tokens,
            "documents": doc_tokens,
            "total": total,
            "remaining": max_tokens - total,
        }
