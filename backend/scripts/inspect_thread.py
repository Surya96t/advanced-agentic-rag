"""
Debug script to inspect a specific thread's checkpoint structure.

Usage:
    python inspect_thread.py <thread_id> [user_id]
    
    Or use environment variable:
    TEST_USER_ID=user_xxx python inspect_thread.py <thread_id>
"""

from psycopg.rows import dict_row
import psycopg
from app.utils.logger import get_logger
from app.core.config import settings
import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


logger = get_logger(__name__)


async def inspect_thread(thread_id: str, user_id: str | None = None):
    """
    Inspect the checkpoint structure for a specific thread.

    Args:
        thread_id: Thread ID to inspect
        user_id: Optional user ID to test thread listing query
    """

    logger.info(f"Inspecting thread: {thread_id}")

    async with await psycopg.AsyncConnection.connect(
        settings.supabase_connection_string,
        autocommit=True,
    ) as conn:
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

                # Safely handle channel_values_keys which may be dict, string, or other type
                channel_values = row['channel_values_keys']
                if channel_values is None:
                    logger.info(f"Channel values keys: None")
                elif isinstance(channel_values, dict):
                    logger.info(
                        f"Channel values keys: {list(channel_values.keys())}")
                elif isinstance(channel_values, str):
                    # Try to parse JSON string
                    try:
                        import json
                        parsed = json.loads(channel_values)
                        if isinstance(parsed, dict):
                            logger.info(
                                f"Channel values keys: {list(parsed.keys())}")
                        else:
                            logger.info(
                                f"Channel values (parsed): {type(parsed).__name__}, length: {len(parsed) if hasattr(parsed, '__len__') else 'N/A'}")
                    except (json.JSONDecodeError, TypeError):
                        logger.info(f"Channel values (string): {channel_values[:100]}..." if len(
                            channel_values) > 100 else f"Channel values (string): {channel_values}")
                else:
                    logger.info(
                        f"Channel values type: {type(channel_values).__name__}, value: {str(channel_values)[:100]}")

                logger.info(f"Metadata full: {row['metadata_full']}")
            else:
                logger.warning(f"No checkpoint found for thread {thread_id}")

        # Now try the query we use in list_user_threads_from_db (if user_id provided)
        if user_id:
            logger.info(f"\nTesting thread listing query for user: {user_id}")

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
                await cur.execute(query2, (user_id,))
                rows = await cur.fetchall()

                logger.info(
                    f"Query with user filter returned {len(rows)} threads:")
                for row in rows:
                    logger.info(
                        f"  - {row['thread_id']} (checkpoint_id: {row['checkpoint_id']})")
        else:
            logger.info(
                "\nSkipping thread listing query (no user_id provided)")
            logger.info(
                "Provide user_id as second argument or set TEST_USER_ID env var to test listing")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Inspect a thread's checkpoint structure",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Inspect thread only
  python inspect_thread.py abc123
  
  # Inspect thread and test user listing
  python inspect_thread.py abc123 user_xyz
  
  # Use environment variable for user ID
  TEST_USER_ID=user_xyz python inspect_thread.py abc123
        """
    )
    parser.add_argument(
        "thread_id",
        nargs="?",
        default="1d893eac-9d98-45b8-9654-587590db0cf4",
        help="Thread ID to inspect (default: 1d893eac-9d98-45b8-9654-587590db0cf4)"
    )
    parser.add_argument(
        "user_id",
        nargs="?",
        help="User ID to test thread listing query (optional, can also use TEST_USER_ID env var)"
    )

    args = parser.parse_args()

    # Get user_id from args or environment variable
    user_id = args.user_id or os.environ.get("TEST_USER_ID")

    asyncio.run(inspect_thread(args.thread_id, user_id))
