"""
LangSmith Service for fetching and aggregating observability metrics.

This service encapsulates all interactions with LangSmith, handling authentication,
caching, and metric aggregation to keep the API layer clean.
"""

import time
from typing import Optional

from cachetools import TTLCache
from langsmith import AsyncClient
from pydantic import BaseModel

from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class LangSmithMetrics(BaseModel):
    """Aggregated metrics from LangSmith runs."""

    total_queries: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    avg_latency_seconds: float = 0.0
    error_rate: float = 0.0


class LangSmithService:
    """
    Service for interacting with LangSmith API to retrieve run data and metrics.
    Includes caching to prevent API rate limits and improve dashboard performance.
    """

    def __init__(self):
        self.api_key = settings.langsmith_api_key
        self.project_name = settings.langsmith_project
        self._client: Optional[AsyncClient] = None

        # Cache for metrics: 5 minutes TTL, max 100 users
        # This matches the previous logic but encapsulates it here
        self._metrics_cache = TTLCache(maxsize=100, ttl=300)

    @property
    def client(self) -> Optional[AsyncClient]:
        """Lazy initialization of the AsyncClient."""
        if not self._client and self.api_key:
            self._client = AsyncClient(
                api_key=self.api_key, api_url="https://api.smith.langchain.com"
            )
        return self._client

    async def get_user_metrics(self, user_id: str, limit: int = 100) -> LangSmithMetrics:
        """
        Fetch and aggregate metrics for a specific user from LangSmith.

        Args:
            user_id: The user ID to filter runs by.
            limit: Max number of recent runs to fetch for aggregation (default 100).

        Returns:
            LangSmithMetrics object with aggregated stats.
        """
        # 1. Check Cache
        if user_id in self._metrics_cache:
            return self._metrics_cache[user_id]

        # 2. Check Configuration
        if not self.client:
            logger.warning("LangSmith API key not set. Returning empty metrics.")
            return LangSmithMetrics()

        start_time = time.time()
        metrics = LangSmithMetrics()

        try:
            logger.info(f"Fetching LangSmith traces for user {user_id}...")

            # Filter for root runs by this user
            # Metadata filter format: and(eq(metadata_key, "user_id"), eq(metadata_value, "value"))
            filter_str = f'and(eq(metadata_key, "user_id"), eq(metadata_value, "{user_id}"))'

            runs = []
            # Fetch runs
            async for run in self.client.list_runs(
                project_name=self.project_name,
                is_root=True,
                filter=filter_str,
                limit=limit,
                select=["id", "status", "start_time", "end_time", "total_tokens", "total_cost"],
            ):
                runs.append(run)

            # 3. Aggregate Metrics
            if not runs:
                logger.info(f"No runs found for user {user_id}")
                return metrics

            total_latency = 0.0
            error_count = 0

            for run in runs:
                # Count
                metrics.total_queries += 1

                # Tokens (handle missing values safely)
                if run.total_tokens:
                    metrics.total_tokens += run.total_tokens

                # Cost
                if run.total_cost:
                    metrics.total_cost += float(run.total_cost)

                # Latency (end_time - start_time)
                if run.end_time and run.start_time:
                    # timestamps are usually datetime objects in the SDK models
                    # but ensure we can handle them if they are strings or objects
                    try:
                        latency = (run.end_time - run.start_time).total_seconds()
                        total_latency += latency
                    except Exception:
                        pass  # specific latency calculation error

                # Errors
                if run.status != "success":
                    error_count += 1

            # Averages
            if metrics.total_queries > 0:
                metrics.avg_latency_seconds = total_latency / metrics.total_queries
                metrics.error_rate = error_count / metrics.total_queries

            # Log performance
            duration = time.time() - start_time
            logger.info(
                f"LangSmith stats aggregated: {metrics.total_queries} runs in {duration:.2f}s "
                f"(Tokens: {metrics.total_tokens}, Cost: ${metrics.total_cost:.4f})"
            )

            # 4. Update Cache
            self._metrics_cache[user_id] = metrics
            return metrics

        except Exception as e:
            logger.error(f"Failed to fetch/aggregate LangSmith metrics: {e}", exc_info=True)
            # Return empty metrics on failure to avoid crashing the dashboard
            return LangSmithMetrics()


# Global instance
langsmith_service = LangSmithService()
