"""
Structured logging configuration using structlog.

This module provides production-grade logging with JSON formatting for
production and pretty console output for development.
"""

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from app.core.config import settings


def add_app_context(_logger: Any, _method_name: str, event_dict: EventDict) -> EventDict:
    """
    Add application context to all log entries.

    Args:
        _logger: The logger instance (unused, required by structlog API)
        _method_name: The logging method name (unused, required by structlog API)
        event_dict: The event dictionary

    Returns:
        EventDict: Updated event dictionary with app context
    """
    event_dict["app"] = settings.app_name
    event_dict["environment"] = settings.environment
    return event_dict


def drop_color_message_key(_logger: Any, _method_name: str, event_dict: EventDict) -> EventDict:
    """
    Remove color_message key from event dict (used by ConsoleRenderer).

    Args:
        _logger: The logger instance (unused, required by structlog API)
        _method_name: The logging method name (unused, required by structlog API)
        event_dict: The event dictionary

    Returns:
        EventDict: Event dictionary without color_message
    """
    event_dict.pop("color_message", None)
    return event_dict


def configure_logging() -> None:
    """
    Configure structlog for the application.

    Sets up different processors based on environment:
    - Production: JSON formatted logs
    - Development: Pretty console logs with colors
    """
    # Common processors for all environments
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        add_app_context,
    ]

    if settings.log_format == "json" or settings.is_production:
        # Production: JSON logs for easy parsing by log aggregators
        processors: list[Processor] = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            drop_color_message_key,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Development: Pretty console logs with colors
        processors = shared_processors + [
            structlog.processors.ExceptionRenderer(),
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Get a configured logger instance.

    Args:
        name: Optional logger name (usually __name__)

    Returns:
        BoundLogger: Configured logger instance

    Example:
        ```python
        from app.utils.logger import get_logger

        logger = get_logger(__name__)
        logger.info("message", key="value")
        logger.error("error occurred", error=str(e))
        ```
    """
    return structlog.get_logger(name)


# Initialize logging on module import
configure_logging()

# Create default logger for this module
logger = get_logger(__name__)
