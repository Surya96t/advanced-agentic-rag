"""
Custom exception classes for the application.

This module defines all custom exceptions used throughout the application
for consistent error handling and response formatting.
"""

from typing import Any


class AppError(Exception):
    """
    Base exception class for all application errors.

    All custom exceptions should inherit from this class.
    """

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize the error.

        Args:
            message: Human-readable error message
            status_code: HTTP status code for the error
            details: Additional error details (optional)
        """
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(AppError):
    """Raised when input validation fails."""

    def __init__(self, message: str = "Validation failed", details: dict[str, Any] | None = None):
        super().__init__(message=message, status_code=400, details=details)


class AuthenticationError(AppError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed", details: dict[str, Any] | None = None):
        super().__init__(message=message, status_code=401, details=details)


class AuthorizationError(AppError):
    """Raised when user lacks permission for an action."""

    def __init__(
        self, message: str = "You don't have permission to access this resource", details: dict[str, Any] | None = None
    ):
        super().__init__(message=message, status_code=403, details=details)


class NotFoundError(AppError):
    """Raised when a requested resource is not found."""

    def __init__(self, message: str = "Resource not found", details: dict[str, Any] | None = None):
        super().__init__(message=message, status_code=404, details=details)


class ConflictError(AppError):
    """Raised when there's a conflict with existing data."""

    def __init__(self, message: str = "Resource already exists", details: dict[str, Any] | None = None):
        super().__init__(message=message, status_code=409, details=details)


class RateLimitError(AppError):
    """Raised when rate limit is exceeded."""

    def __init__(
        self, message: str = "Rate limit exceeded. Please try again later.", details: dict[str, Any] | None = None
    ):
        super().__init__(message=message, status_code=429, details=details)


class DatabaseError(AppError):
    """Raised when a database operation fails."""

    def __init__(self, message: str = "Database operation failed", details: dict[str, Any] | None = None):
        super().__init__(message=message, status_code=500, details=details)


class ExternalServiceError(AppError):
    """Raised when an external service (OpenAI, Supabase, etc.) fails."""

    def __init__(self, message: str = "External service error", details: dict[str, Any] | None = None):
        super().__init__(message=message, status_code=502, details=details)


class EmbeddingError(AppError):
    """Raised when embedding generation fails."""

    def __init__(self, message: str = "Failed to generate embeddings", details: dict[str, Any] | None = None):
        super().__init__(message=message, status_code=500, details=details)


class ChunkingError(AppError):
    """Raised when document chunking fails."""

    def __init__(self, message: str = "Failed to chunk document", details: dict[str, Any] | None = None):
        super().__init__(message=message, status_code=500, details=details)


class DocumentProcessingError(AppError):
    """Raised when document processing fails."""

    def __init__(self, message: str = "Failed to process document", details: dict[str, Any] | None = None):
        super().__init__(message=message, status_code=500, details=details)


class RetrievalError(AppError):
    """Raised when document retrieval fails."""

    def __init__(self, message: str = "Failed to retrieve documents", details: dict[str, Any] | None = None):
        super().__init__(message=message, status_code=500, details=details)


class LLMError(AppError):
    """Raised when LLM operation fails."""

    def __init__(self, message: str = "LLM operation failed", details: dict[str, Any] | None = None):
        super().__init__(message=message, status_code=500, details=details)
