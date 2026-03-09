"""
Structured observability utilities for LangGraph agent nodes.

Provides trace_node_execution (async context manager) and trace_node (decorator)
for emitting structured start / complete / error log events around each node body.
Both work alongside LangSmith traces — they add per-node structlog entries that
can be parsed by log aggregators (JSON in prod, pretty-print in dev).
"""

import functools
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Awaitable, Callable, Optional, ParamSpec, TypeVar

from app.utils.logger import get_logger

P = ParamSpec("P")
R = TypeVar("R")

logger = get_logger(__name__)


@asynccontextmanager
async def trace_node_execution(
    node_name: str,
    state: dict[str, Any],
) -> AsyncGenerator[None, None]:
    """
    Async context manager that emits structured log events around a node body.

    Logs:
    - ``node_start``    — before the body runs (includes thread_id, query_preview)
    - ``node_complete`` — after normal exit (includes duration_ms)
    - ``node_error``    — if an unhandled exception escapes (re-raises)

    Args:
        node_name: Logical node label (e.g. "classifier", "retriever").
        state:     Current AgentState dict used to extract user_id / query preview.

    Example::

        async with trace_node_execution("classifier", state):
            return await _do_classify(state)
    """
    start = time.time()
    user_id: str = state.get("user_id", "unknown")
    query_preview: str = str(
        state.get("original_query") or state.get("query") or ""
    )[:80]

    logger.info(
        "node_start",
        node=node_name,
        user_id=user_id,
        query_preview=query_preview,
    )

    try:
        yield
        logger.info(
            "node_complete",
            node=node_name,
            user_id=user_id,
            duration_ms=round((time.time() - start) * 1000, 1),
        )
    except Exception as e:
        logger.error(
            "node_error",
            node=node_name,
            user_id=user_id,
            duration_ms=round((time.time() - start) * 1000, 1),
            error=str(e),
        )
        raise


def trace_node(name: str):
    """
    Decorator that wraps an async LangGraph node function with trace_node_execution.

    ``functools.wraps`` preserves ``__wrapped__`` so ``inspect.signature()``
    returns the original function's signature — LangGraph uses this to decide
    whether to inject the ``RunnableConfig`` second argument.

    Args:
        name: Logical node label used in log events.

    Example::

        @trace_node("classifier")
        async def classify_query(state: AgentState) -> Command:
            ...
    """

    def decorator(fn: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @functools.wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # First positional arg is always AgentState for every node type
            state: Optional[dict[str, Any]] = args[0] if args else kwargs.get("state")  # type: ignore[assignment]
            if state is None:
                logger.warning(
                    "trace_node wrapper received no state",
                    node=name,
                    func=fn.__name__,
                    args_count=len(args),
                    kwarg_keys=list(kwargs.keys()),
                )
                state = {}
            async with trace_node_execution(name, state):
                return await fn(*args, **kwargs)

        return wrapper

    return decorator
