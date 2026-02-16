from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import UserID
from app.database.client import SupabaseClient
from app.utils.logger import get_logger
from app.core.config import settings

router = APIRouter(prefix="/api/v1/stats", tags=["stats"])
logger = get_logger(__name__)


class DashboardStats(BaseModel):
    """
    Validation schema for dashboard statistics response.
    """
    documents_count: int
    chunks_count: int
    conversations_count: int
    queries_count: int


@router.get("/", response_model=DashboardStats)
async def get_dashboard_stats(
    user_id: UserID
) -> DashboardStats:
    """
    Get dashboard statistics for the authenticated user.

    Fetches counts for:
    - Documents (from documents table)
    - Chunks (from document_chunks table)
    - Conversations (unique threads from checkpoints table)
    - Queries (Estimated from message counts)
    """
    try:
        # 1. Get counts from Supabase tables (fast)
        supabase = SupabaseClient.get_client()
        
        # Count documents
        docs_res = supabase.table("documents") \
            .select("id", count="exact") \
            .eq("user_id", user_id) \
            .execute()
        docs_count = docs_res.count if docs_res.count is not None else 0
        
        # Count chunks
        chunks_res = supabase.table("document_chunks") \
            .select("id", count="exact") \
            .eq("user_id", user_id) \
            .execute()
        chunks_count = chunks_res.count if chunks_res.count is not None else 0

        # 2. Get conversation and query stats from Checkpoints (complex SQL)
        # We use raw SQL here because Supabase client doesn't expose the checkpoints table easily
        # (it's part of LangGraph persistence layer) and we need to parse JSONB.
        from psycopg import AsyncConnection
        
        conversations_count = 0
        queries_count = 0
        
        # Query to count unique threads and estimate queries
        # We look for the latest checkpoint for each thread to get the current message count
        # Queries ≈ total messages / 2 (assuming User + Assistant pairs)
        query = """
        WITH latest_checkpoints AS (
            SELECT DISTINCT ON (thread_id)
                thread_id,
                checkpoint
            FROM checkpoints
            WHERE checkpoint_ns = ''
              AND checkpoint->'channel_values'->>'user_id' = %s
            ORDER BY thread_id, checkpoint_id DESC
        )
        SELECT 
            COUNT(*) as thread_count,
            SUM(jsonb_array_length(checkpoint->'channel_values'->'messages')) as total_messages
        FROM latest_checkpoints
        """
        
        try:
            async with await AsyncConnection.connect(settings.supabase_connection_string) as conn:
                async with conn.cursor() as cur:
                    await cur.execute(query, (user_id,))
                    row = await cur.fetchone()
                    if row:
                        conversations_count = row[0]
                        total_messages = row[1] if row[1] is not None else 0
                        # Estimate queries as half of total messages (user + assistant)
                        queries_count = total_messages // 2
        except Exception as db_err:
            logger.error(f"Failed to fetch stats from checkpoints: {db_err}")
            # Fallback to 0 if DB query fails, don't crash the whole endpoint

        return DashboardStats(
            documents_count=docs_count,
            chunks_count=chunks_count,
            conversations_count=conversations_count,
            queries_count=queries_count
        )

    except Exception as e:
        logger.error(
            "Error fetching dashboard stats",
            error=str(e),
            user_id=user_id,
        )
        # Return zeros on error to allow dashboard to render
        return DashboardStats(
            documents_count=0,
            chunks_count=0,
            conversations_count=0,
            queries_count=0,
        )
