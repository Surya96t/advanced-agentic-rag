"""
Message trimming strategies for managing conversation history.

This module provides utilities to trim message history when it exceeds
token limits, ensuring critical context is preserved.
"""

from langchain_core.messages import BaseMessage, SystemMessage

from app.utils.token_counter import TokenCounter


class MessageTrimmer:
    """Strategies for trimming conversation history."""

    def __init__(self, token_counter: TokenCounter):
        """
        Initialize message trimmer with token counter.

        Args:
            token_counter: TokenCounter instance for counting tokens
        """
        self.counter = token_counter

    def trim_to_token_limit(
        self,
        messages: list[BaseMessage],
        max_tokens: int,
        keep_recent: int = 6,  # Keep last 3 exchanges (user + assistant)
    ) -> list[BaseMessage]:
        """
        Trim messages to fit within token limit.

        Strategy:
        1. Always keep system messages
        2. Always keep last N messages (recent context)
        3. Remove oldest messages first until within limit

        Args:
            messages: Full message history
            max_tokens: Maximum token limit
            keep_recent: Number of recent messages to always keep

        Returns:
            Trimmed message list within token limit

        Example:
            >>> counter = TokenCounter("gpt-4")
            >>> trimmer = MessageTrimmer(counter)
            >>> messages = [SystemMessage(...), HumanMessage(...), ...]  # 100 messages
            >>> trimmed = trimmer.trim_to_token_limit(messages, max_tokens=1000)
            >>> len(trimmed) < len(messages)
            True
        """
        # If already within limit, return as-is
        if self.counter.count_messages_tokens(messages) <= max_tokens:
            return messages

        # Separate message types
        system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
        other_msgs = [m for m in messages if not isinstance(m, SystemMessage)]

        # Keep recent messages
        recent = other_msgs[-keep_recent:]
        older = other_msgs[:-keep_recent]

        # Calculate tokens used by system + recent
        base_tokens = self.counter.count_messages_tokens(
            system_msgs
        ) + self.counter.count_messages_tokens(recent)

        # Add older messages until limit
        remaining_tokens = max_tokens - base_tokens
        trimmed_older = []

        # Add from oldest to newest until we hit limit
        for msg in reversed(older):
            msg_tokens = self.counter.count_message_tokens(msg)
            if msg_tokens <= remaining_tokens:
                trimmed_older.insert(0, msg)
                remaining_tokens -= msg_tokens
            else:
                break

        return system_msgs + trimmed_older + recent

    def create_sliding_window(
        self, messages: list[BaseMessage], window_size: int = 10
    ) -> list[BaseMessage]:
        """
        Simple sliding window: keep system + last N messages.

        Args:
            messages: Full message history
            window_size: Number of recent messages to keep

        Returns:
            Messages within sliding window

        Example:
            >>> counter = TokenCounter("gpt-4")
            >>> trimmer = MessageTrimmer(counter)
            >>> messages = [...]  # 50 messages
            >>> windowed = trimmer.create_sliding_window(messages, window_size=10)
            >>> len(windowed) <= 11  # System msg + 10 recent
            True
        """
        system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
        other_msgs = [m for m in messages if not isinstance(m, SystemMessage)]

        return system_msgs + other_msgs[-window_size:]
