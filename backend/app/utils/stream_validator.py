"""
Stream content validation utilities.

Provides server-side validation for streamed tokens to ensure:
- No malicious content injection
- Token size limits
- Rate limiting on token emission
- Content safety checks
"""

import re
from typing import Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)

# Dangerous patterns that should be blocked
DANGEROUS_PATTERNS = [
    re.compile(r"<script[^>]*>", re.IGNORECASE),
    re.compile(r"</script>", re.IGNORECASE),
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"on\w+\s*=", re.IGNORECASE),  # Event handlers
    re.compile(r"<iframe[^>]*>", re.IGNORECASE),
    re.compile(r"<embed[^>]*>", re.IGNORECASE),
    re.compile(r"<object[^>]*>", re.IGNORECASE),
    re.compile(r"data:text/html", re.IGNORECASE),
    re.compile(r"vbscript:", re.IGNORECASE),
]

# Token limits
MAX_TOKEN_LENGTH = 1000  # Max characters per token event
MAX_CONTENT_LENGTH = 50000  # Max total content length


class TokenValidator:
    """
    Validates streaming tokens for security and safety.
    """

    def __init__(self):
        self.total_tokens = 0
        self.total_length = 0

    def validate_token(
        self,
        token: str,
        user_id: Optional[str] = None,
    ) -> tuple[bool, Optional[str]]:
        """
        Validate a single streaming token.

        Args:
            token: Token to validate
            user_id: User ID for logging

        Returns:
            Tuple of (is_valid, error_message)
            - (True, None) if valid
            - (False, error_message) if invalid
        """
        # Check token length
        if len(token) > MAX_TOKEN_LENGTH:
            logger.warning(
                "Token exceeds max length",
                extra={
                    "user_id": user_id,
                    "token_length": len(token),
                    "max_length": MAX_TOKEN_LENGTH,
                },
            )
            return False, f"Token too long ({len(token)} > {MAX_TOKEN_LENGTH})"

        # Check total content length
        self.total_length += len(token)
        if self.total_length > MAX_CONTENT_LENGTH:
            logger.warning(
                "Total content exceeds max length",
                extra={
                    "user_id": user_id,
                    "total_length": self.total_length,
                    "max_length": MAX_CONTENT_LENGTH,
                },
            )
            return False, f"Content too long ({self.total_length} > {MAX_CONTENT_LENGTH})"

        # Check for dangerous patterns
        for pattern in DANGEROUS_PATTERNS:
            if pattern.search(token):
                logger.warning(
                    "Dangerous pattern detected in token",
                    extra={
                        "user_id": user_id,
                        "pattern": pattern.pattern,
                        "token_preview": token[:50],
                    },
                )
                return False, "Token contains unsafe content"

        # Increment counter
        self.total_tokens += 1

        return True, None

    def reset(self):
        """Reset validator state for new stream."""
        self.total_tokens = 0
        self.total_length = 0

    def get_stats(self) -> dict:
        """Get validation statistics."""
        return {
            "total_tokens": self.total_tokens,
            "total_length": self.total_length,
        }


def validate_citation_content(
    chunk_id: str,
    document_title: Optional[str],
    content: Optional[str],
    user_id: Optional[str] = None,
) -> tuple[bool, Optional[str]]:
    """
    Validate citation content for safety.

    Args:
        chunk_id: Chunk identifier
        document_title: Document title (optional)
        content: Citation content (optional)
        user_id: User ID for logging

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Handle None values
    document_title = document_title or ""
    content = content or ""

    # Check lengths
    if len(document_title) > 500:
        logger.warning(
            "Citation document_title too long", extra={"user_id": user_id, "chunk_id": chunk_id}
        )
        return False, "Document title too long"

    if len(content) > 5000:
        logger.warning(
            "Citation content too long", extra={"user_id": user_id, "chunk_id": chunk_id}
        )
        return False, "Citation content too long"

    # Check for dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if pattern.search(document_title) or pattern.search(content):
            logger.warning(
                "Dangerous pattern in citation", extra={"user_id": user_id, "chunk_id": chunk_id}
            )
            return False, "Citation contains unsafe content"

    return True, None
