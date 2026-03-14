
import asyncio

from cachetools import TTLCache
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.deps import UserID
from app.core.langsmith_service import LangSmithMetrics, langsmith_service
from app.database.client import SupabaseClient
from app.database.pool import DatabasePool
from app.utils.logger import get_logger

router = APIRouter(prefix="/api/v1/stats", tags=["stats"])
logger = get_logger(__name__)

# Initialize caches
# DB Stats: Cache for 30 seconds, max 100 users
# Reason: Internal DB, fast (<100ms), but good to debounce rapid refreshes
db_stats_cache = TTLCache(maxsize=100, ttl=30)


class DashboardStats(BaseModel):
    """
    Validation schema for dashboard statistics response.
    """
    # Database stats
    documents_count: int
    chunks_count: int
    conversations_count: int

    # Observability stats (LangSmith)
    queries_count: int = Field(..., description="Total number of queries run")
    total_tokens: int = Field(0, description="Total tokens consumed")
    total_cost: float = Field(0.0, description="Total estimated cost in USD")
    avg_latency_seconds: float = Field(0.0, description="Average response latency in seconds")
    error_rate: float = Field(0.0, description="Percentage of failed runs (0.0-1.0)")

# --- Helper Functions for Parallel Execution ---

async def count_user_documents(user_id: str) -> int:
    try:
        supabase = SupabaseClient.get_client()
        res = supabase.table("documents").select("id", count="exact").eq("user_id", user_id).execute()
        return res.count if res.count is not None else 0
    except Exception as e:
        logger.error(f"Failed to count documents: {e}")
        return 0

async def count_user_chunks(user_id: str) -> int:
    try:
        supabase = SupabaseClient.get_client()
        res = supabase.table("document_chunks").select("id", count="exact").eq("user_id", user_id).execute()
        return res.count if res.count is not None else 0
    except Exception as e:
        logger.error(f"Failed to count chunks: {e}")
        return 0

async def count_user_conversations(user_id: str) -> int:
    try:
        query = """
            SELECT COUNT(DISTINCT thread_id)
            FROM checkpoints
            WHERE checkpoint_ns = ''
              AND metadata->>'user_id' = %s
              AND (
                checkpoint->'channel_values'->>'query' IS NOT NULL
                OR checkpoint->'channel_values'->>'generated_response' IS NOT NULL
              )
              AND checkpoint->'channel_values'->>'user_id' = %s
        """
        async with DatabasePool.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (user_id, user_id))
                row = await cur.fetchone()
                return row[0] if row else 0
    except Exception as e:
        logger.error(f"Failed to count conversations: {e}")
        return 0

async def get_db_stats(user_id: str) -> tuple[int, int, int]:
    """Helper to get DB stats with simple caching."""
    # Check cache first (DB stats change on explicit actions, can be slightly stale)
    if user_id in db_stats_cache:
        return db_stats_cache[user_id]

    try:
        # Run DB queries in parallel
        # Documents and chunks use PostgREST (HTTP), Conversations use SQL (TCP)
        results = await asyncio.gather(
            count_user_documents(user_id),
            count_user_chunks(user_id),
            count_user_conversations(user_id),
            return_exceptions=True
        )

        # Unpack safely
        docs = results[0] if isinstance(results[0], int) else 0
        chunks = results[1] if isinstance(results[1], int) else 0
        convs = results[2] if isinstance(results[2], int) else 0

        # Store in cache
        stats_tuple = (docs, chunks, convs)
        db_stats_cache[user_id] = stats_tuple
        return stats_tuple

    except Exception as e:
        logger.error(f"Failed to fetch DB stats: {e}")
        return (0, 0, 0)


@router.get("/", response_model=DashboardStats)
async def get_dashboard_stats(
    user_id: UserID
) -> DashboardStats:
    """
    Get dashboard statistics for the authenticated user.

    Uses aggressive parallel execution and caching to minimize latency.
    Avg response time should be < 100ms on cache hit.
    """
    try:
        # 1. Fetch DB Stats (Fast, cached 30s)
        # 2. Fetch LangSmith Stats via Service (Slow, cached 5m internal to service)

        db_task = asyncio.create_task(get_db_stats(user_id))
        ls_task = asyncio.create_task(langsmith_service.get_user_metrics(user_id))

        # Run main tasks in parallel
        # Note: exceptions return as instances in results list
        results = await asyncio.gather(db_task, ls_task, return_exceptions=True)

        db_res = results[0]
        ls_res = results[1]

        # Unpack DB Stats
        docs, chunks, convs = (0, 0, 0)
        if isinstance(db_res, tuple) and len(db_res) == 3:
            docs, chunks, convs = db_res
        elif isinstance(db_res, Exception):
            logger.error(f"DB Stats Task failed: {db_res}")

        # Unpack LS Stats
        ls_metrics = LangSmithMetrics() # Default empty
        if isinstance(ls_res, LangSmithMetrics):
            ls_metrics = ls_res
        elif isinstance(ls_res, Exception):
            logger.error(f"LS Service Task failed: {ls_res}")

        return DashboardStats(
            documents_count=docs,
            chunks_count=chunks,
            conversations_count=convs,
            # Mapped from service metrics
            queries_count=ls_metrics.total_queries,
            total_tokens=ls_metrics.total_tokens,
            total_cost=ls_metrics.total_cost,
            avg_latency_seconds=ls_metrics.avg_latency_seconds,
            error_rate=ls_metrics.error_rate
        )

    except Exception as e:
        logger.error(
            "Critical error fetching dashboard stats",
            error=str(e),
            user_id=user_id,
        )
        return DashboardStats(
            documents_count=0,
            chunks_count=0,
            conversations_count=0,
            queries_count=0,
        )
