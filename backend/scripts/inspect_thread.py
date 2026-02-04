"""
Debug script to inspect a specific thread's checkpoint structure.
"""

from psycopg.rows import dict_row
import psycopg
from app.utils.logger import get_logger
from app.core.config import settings
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


logger = get_logger(__name__)


async def inspect_thread(thread_id: str):
    """Inspect the checkpoint structure for a specific thread."""

    logger.info(f"Inspecting thread: {thread_id}")

    conn = await psycopg.AsyncConnection.connect(
        settings.supabase_connection_string,
        autocommit=True,
    )

    try:
        # Get the latest checkpoint for this thread
        query = """
        SELECT 
            thread_id,
            checkpoint_id,
            checkpoint->'channel_values'->>'user_id' as state_user_id,
            metadata->>'user_id' as metadata_user_id,
            checkpoint->'channel_values' as channel_values_keys,
            metadata as metadata_full
        FROM checkpoints
        WHERE thread_id = %s
          AND checkpoint_ns = ''
        ORDER BY checkpoint_id DESC
        LIMIT 1
        """

        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(query, (thread_id,))
            row = await cur.fetchone()

            if row:
                logger.info(f"Found checkpoint for thread {thread_id}")
                logger.info(f"Checkpoint ID: {row['checkpoint_id']}")
                logger.info(f"State user_id: {row['state_user_id']}")
                logger.info(f"Metadata user_id: {row['metadata_user_id']}")
                logger.info(
                    f"Channel values keys: {list(row['channel_values_keys'].keys()) if row['channel_values_keys'] else None}")
                logger.info(f"Metadata full: {row['metadata_full']}")
            else:
                logger.warning(f"No checkpoint found for thread {thread_id}")

        # Now try the query we use in list_user_threads_from_db
        test_user_id = "user_38lGIpoZe2YU3DBkdrTeBzXsIMD"  # Your user ID from logs

        query2 = """
        WITH latest_checkpoints AS (
            SELECT DISTINCT ON (thread_id)
                thread_id,
                checkpoint,
                metadata,
                checkpoint_id
            FROM checkpoints
            WHERE checkpoint_ns = ''
              AND checkpoint->'channel_values'->>'user_id' = %s
            ORDER BY thread_id, checkpoint_id DESC
        )
        SELECT
            thread_id,
            checkpoint_id
        FROM latest_checkpoints
        ORDER BY checkpoint_id DESC
        """

        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(query2, (test_user_id,))
            rows = await cur.fetchall()

            logger.info(
                f"\nQuery with user filter returned {len(rows)} threads:")
            for row in rows:
                logger.info(
                    f"  - {row['thread_id']} (checkpoint_id: {row['checkpoint_id']})")

    finally:
        await conn.close()


if __name__ == "__main__":
    thread_id = sys.argv[1] if len(
        sys.argv) > 1 else "1d893eac-9d98-45b8-9654-587590db0cf4"
    asyncio.run(inspect_thread(thread_id))
