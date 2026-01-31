"""
Stream observability metrics.

Provides hooks for tracking stream performance and reliability:
- Connection success/failure rates
- Stream latency measurements
- Token throughput
- Error rates by type
"""

import time
from dataclasses import dataclass, field
from typing import Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class StreamMetrics:
    """Metrics for a single streaming session."""

    # Session info
    user_id: str
    thread_id: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None

    # Connection metrics
    connection_success: bool = False
    connection_latency_ms: Optional[float] = None

    # Stream metrics
    tokens_sent: int = 0
    citations_sent: int = 0
    events_sent: int = 0
    bytes_sent: int = 0

    # Agent metrics
    agents_executed: list[str] = field(default_factory=list)
    agent_durations: dict[str, float] = field(default_factory=dict)

    # Error metrics
    errors: list[str] = field(default_factory=list)
    disconnected: bool = False
    cancelled: bool = False

    def record_connection_success(self, latency_ms: float):
        """Record successful connection."""
        self.connection_success = True
        self.connection_latency_ms = latency_ms

    def record_token(self, token: str):
        """Record a streamed token."""
        self.tokens_sent += 1
        self.bytes_sent += len(token.encode('utf-8'))
        self.events_sent += 1

    def record_citation(self):
        """Record a citation event."""
        self.citations_sent += 1
        self.events_sent += 1

    def record_agent_start(self, agent: str):
        """Record agent execution start."""
        self.agents_executed.append(agent)

    def record_agent_complete(self, agent: str, duration_ms: float):
        """Record agent execution completion."""
        self.agent_durations[agent] = duration_ms

    def record_error(self, error: str):
        """Record an error."""
        self.errors.append(error)

    def record_disconnect(self):
        """Record client disconnect."""
        self.disconnected = True
        self.end_time = time.time()

    def record_cancel(self):
        """Record client cancellation."""
        self.cancelled = True
        self.end_time = time.time()

    def finalize(self):
        """Finalize metrics and log."""
        if self.end_time is None:
            self.end_time = time.time()

        duration_s = self.end_time - self.start_time

        # Log comprehensive metrics
        logger.info(
            "Stream completed",
            extra={
                "user_id": self.user_id,
                "thread_id": self.thread_id,
                "duration_s": round(duration_s, 2),
                "connection_success": self.connection_success,
                "connection_latency_ms": self.connection_latency_ms,
                "tokens_sent": self.tokens_sent,
                "citations_sent": self.citations_sent,
                "events_sent": self.events_sent,
                "bytes_sent": self.bytes_sent,
                "agents_executed": self.agents_executed,
                "agent_durations_ms": self.agent_durations,
                "error_count": len(self.errors),
                "disconnected": self.disconnected,
                "cancelled": self.cancelled,
                "tokens_per_second": round(self.tokens_sent / duration_s, 2) if duration_s > 0 else 0,
            }
        )

        # Log errors separately if any
        if self.errors:
            logger.warning(
                "Stream errors",
                extra={
                    "user_id": self.user_id,
                    "thread_id": self.thread_id,
                    "errors": self.errors,
                }
            )

    def to_dict(self) -> dict:
        """Export metrics as dictionary."""
        duration_s = (self.end_time or time.time()) - self.start_time
        return {
            "user_id": self.user_id,
            "thread_id": self.thread_id,
            "duration_s": duration_s,
            "connection_success": self.connection_success,
            "connection_latency_ms": self.connection_latency_ms,
            "tokens_sent": self.tokens_sent,
            "citations_sent": self.citations_sent,
            "events_sent": self.events_sent,
            "bytes_sent": self.bytes_sent,
            "agents_executed": self.agents_executed,
            "agent_durations_ms": self.agent_durations,
            "errors": self.errors,
            "disconnected": self.disconnected,
            "cancelled": self.cancelled,
        }
