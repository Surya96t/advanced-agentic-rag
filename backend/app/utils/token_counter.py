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

        # Try to get model-specific encoding, fall back to cl100k_base for unknown models
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            # Model not recognized, use cl100k_base (GPT-4 default encoding)
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"Model '{model}' not recognized by tiktoken. "
                f"Falling back to 'cl100k_base' encoding."
            )
            self.encoding = tiktoken.get_encoding("cl100k_base")

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
        # Normalize message content to string
        content = message.content
        if content is None:
            normalized_content = ""
        elif isinstance(content, list):
            # Handle multimodal content (list of blocks)
            # Extract only textual fields from dicts to avoid counting metadata/URLs
            parts = []
            for item in content:
                if item is None:
                    continue

                if isinstance(item, dict):
                    # Extract known textual fields from multimodal content blocks
                    # Common fields: "text" (text blocks), "caption" (images), "alt" (images), "content"
                    textual_fields = ["text", "content",
                                      "caption", "alt", "description"]
                    extracted_text = None

                    for field in textual_fields:
                        if field in item and isinstance(item.get(field), str):
                            extracted_text = item[field]
                            break

                    if extracted_text:
                        parts.append(extracted_text)
                    # If no textual field found, skip this item (e.g., image_url blocks)
                elif isinstance(item, str):
                    # Plain string in list
                    parts.append(item)
                # Skip other types (e.g., binary data, complex objects)

            normalized_content = " ".join(parts)
        elif isinstance(content, str):
            normalized_content = content
        else:
            # Fallback for other types (should be rare)
            normalized_content = str(content)

        # Count message content
        tokens = len(self.encoding.encode(normalized_content))

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

        # Model-specific context window limits
        # Check for exact matches first, then patterns
        model_context_limits = {
            # GPT-4 models
            "gpt-4": 8192,
            "gpt-4-0314": 8192,
            "gpt-4-0613": 8192,
            "gpt-4-32k": 32768,
            "gpt-4-32k-0314": 32768,
            "gpt-4-32k-0613": 32768,
            "gpt-4-turbo": 128000,
            "gpt-4-turbo-preview": 128000,
            "gpt-4-1106-preview": 128000,
            "gpt-4o": 128000,
            "gpt-4o-mini": 128000,
            # GPT-3.5 models
            "gpt-3.5-turbo": 4096,
            "gpt-3.5-turbo-0301": 4096,
            "gpt-3.5-turbo-0613": 4096,
            "gpt-3.5-turbo-16k": 16384,
            "gpt-3.5-turbo-16k-0613": 16384,
        }

        # Try exact match first
        max_tokens = model_context_limits.get(self.model)

        # If no exact match, check for patterns in model name
        # IMPORTANT: Check GPT-3.5 BEFORE generic "turbo" to avoid assigning 128K to GPT-3.5 models
        if max_tokens is None:
            if "gpt-3.5" in self.model or "3.5" in self.model:
                # GPT-3.5 variants: check for 16k, otherwise default to 4k
                if "16k" in self.model:
                    max_tokens = 16384
                else:
                    max_tokens = 4096
            elif "gpt-4o" in self.model:
                max_tokens = 128000
            elif "32k" in self.model:
                max_tokens = 32768
            elif "16k" in self.model:
                max_tokens = 16384
            elif "turbo" in self.model:
                # Generic turbo models (likely GPT-4 turbo variants)
                max_tokens = 128000
            else:
                # Default fallback for unknown models
                max_tokens = 8192

        # Calculate remaining tokens, ensuring it's never negative
        remaining = max(0, max_tokens - total)

        return {
            "messages": msg_tokens,
            "system": sys_tokens,
            "documents": doc_tokens,
            "total": total,
            "remaining": remaining,
        }
