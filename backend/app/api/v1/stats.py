from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import UserID
from app.database.client import SupabaseClient
from app.database.pool import DatabasePool
from app.utils.logger import get_logger
from app.core.config import settings
from langsmith import AsyncClient
import asyncio
from cachetools import TTLCache
import time

router = APIRouter(prefix="/api/v1/stats", tags=["stats"])
logger = get_logger(__name__)

# Initialize caches
# LangSmith Queries: Cache for 5 minutes (300s), max 100 users
# Reason: External API call, slow (1-3s), data doesn't change implicitly (only on user action)
queries_cache = TTLCache(maxsize=100, ttl=300)

# DB Stats: Cache for 30 seconds, max 100 users
# Reason: Internal DB, fast (<100ms), but good to debounce rapid refreshes
db_stats_cache = TTLCache(maxsize=100, ttl=30)



class DashboardStats(BaseModel):
    """
    Validation schema for dashboard statistics response.
    """
    documents_count: int
    chunks_count: int
    conversations_count: int
    queries_count: int

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


async def count_user_queries_cached(user_id: str) -> int:
    """Get LangSmith query count with aggressive TTL caching."""
    
    # HIT: Return valid cached value
    if user_id in queries_cache:
        val = queries_cache[user_id]
        return val

    # MISS: Fetch from API
    if not settings.langsmith_api_key:
        logger.warning("LangSmith API key not set")
        return 0
        
    start_time = time.time()
    try:
        logger.info(f"Fetching LangSmith stats for user {user_id}...")
        
        # Use simple client to fetch just the count if possible, 
        # but list_runs is the standard way.
        # Pass API key explicitly from settings
        client = AsyncClient(api_key=settings.langsmith_api_key, api_url="https://api.smith.langchain.com")
        filter_str = f'and(eq(metadata_key, "user_id"), eq(metadata_value, "{user_id}"))'
        
        runs = []
        # Optimization: Fetch ONLY 100 items per page (API max)
        # We cap at 100 for now to avoid pagination overhead on dashboard
        async for run in client.list_runs(
            project_name=settings.langsmith_project,
            is_root=True,
            filter=filter_str,
            limit=100, 
            select=["id"] 
        ):
            runs.append(run)
            
        count = len(runs)
        logger.info(f"LangSmith stats fetched: {count} runs")
        
        # Log slow calls
        duration = time.time() - start_time
        if duration > 1.0:
            logger.warning(f"LangSmith stats query took {duration:.2f}s")
            
        # Only cache positive results to avoid caching transient failures as "0"
        # Since this is for a dashboard, if we fail to fetch, we'd rather try again 
        # on next refresh than show 0 for 5 minutes.
        if count > 0:
            queries_cache[user_id] = count
            
        return count
        
    except Exception as e:
        logger.error(f"Failed to count queries from LangSmith: {e}")
        # Build filter manually just in case
        return 0

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
        # 2. Fetch Query Stats (Slow, cached 5m)
        
        db_task = asyncio.create_task(get_db_stats(user_id))
        ls_task = asyncio.create_task(count_user_queries_cached(user_id))
        
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
        queries = 0
        if isinstance(ls_res, int):
            queries = ls_res
        elif isinstance(ls_res, Exception):
            logger.error(f"LS Stats Task failed: {ls_res}")
            
        return DashboardStats(
            documents_count=docs,
            chunks_count=chunks,
            conversations_count=convs,
            queries_count=queries
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
