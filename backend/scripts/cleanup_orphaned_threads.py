"""
Cleanup script for orphaned threads without user_id.

This script deletes all threads (checkpoints) that have `user_id: None` in their state.
These are threads created before the user_id ownership fix was implemented.

Usage:
    python -m scripts.cleanup_orphaned_threads

Safety:
    - Dry-run mode by default (shows what would be deleted)
    - Use --execute flag to actually delete
    - Prompts for confirmation before deleting
"""

import psycopg
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from app.utils.logger import get_logger
from app.core.config import settings
import argparse
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))


logger = get_logger(__name__)


async def find_orphaned_threads(checkpointer: AsyncPostgresSaver) -> list[str]:
    """
    Find all threads with user_id: None in their state.

    Args:
        checkpointer: LangGraph checkpointer instance

    Returns:
        List of thread IDs that are orphaned
    """
    conn = checkpointer.conn

    # Query for all unique thread_ids and check their user_id
    query = """
    SELECT DISTINCT ON (thread_id)
        thread_id,
        checkpoint
    FROM checkpoints
    WHERE checkpoint_ns = ''
    ORDER BY thread_id, checkpoint_id DESC
    """

    from psycopg.rows import dict_row

    orphaned_thread_ids = []

    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(query)
        rows = await cur.fetchall()

        logger.info(f"Found {len(rows)} total threads in database")

        for row in rows:
            thread_id = row['thread_id']

            # Deserialize checkpoint to check user_id
            checkpoint_data = row['checkpoint']

            try:
                # The checkpoint is already deserialized by psycopg3's JSONB support
                # Access channel_values to get state
                state = checkpoint_data.get('channel_values', {})
                user_id = state.get('user_id')

                if user_id is None:
                    orphaned_thread_ids.append(thread_id)
                    logger.debug(
                        f"Thread {thread_id}: ORPHANED (user_id: None)")
                else:
                    logger.debug(f"Thread {thread_id}: owned by {user_id}")

            except Exception as e:
                logger.error(f"Error checking thread {thread_id}: {e}")
                continue

    return orphaned_thread_ids


async def delete_thread_checkpoints(checkpointer: AsyncPostgresSaver, thread_id: str) -> bool:
    """
    Delete all checkpoints for a given thread.

    Args:
        checkpointer: LangGraph checkpointer instance
        thread_id: Thread identifier

    Returns:
        True if successful, False otherwise
    """
    try:
        conn = checkpointer.conn

        delete_query = """
        DELETE FROM checkpoints
        WHERE thread_id = %s
        """

        async with conn.cursor() as cur:
            await cur.execute(delete_query, (thread_id,))
            deleted_count = cur.rowcount
            logger.info(
                f"Deleted {deleted_count} checkpoint(s) for thread {thread_id}")

        return True

    except Exception as e:
        logger.error(f"Error deleting thread {thread_id}: {e}")
        return False


async def main(dry_run: bool = True):
    """
    Main cleanup function.

    Args:
        dry_run: If True, only shows what would be deleted without actually deleting
    """
    logger.info("=" * 60)
    logger.info("Orphaned Thread Cleanup Script")
    logger.info("=" * 60)
    logger.info(
        f"Mode: {'DRY RUN (no changes)' if dry_run else 'EXECUTE (will delete)'}")
    logger.info(f"Database: {settings.supabase_connection_string[:50]}...")
    logger.info("")

    # Create checkpointer connection
    logger.info("Connecting to database...")
    try:
        conn = await psycopg.AsyncConnection.connect(
            settings.supabase_connection_string,
            autocommit=False,  # Use transactions for safety
            prepare_threshold=0,
        )
        checkpointer = AsyncPostgresSaver(conn)
        await checkpointer.setup()
        logger.info("✓ Connected successfully")
        logger.info("")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return

    try:
        # Find orphaned threads
        logger.info("Scanning for orphaned threads...")
        orphaned_threads = await find_orphaned_threads(checkpointer)

        logger.info("")
        logger.info(f"Found {len(orphaned_threads)} orphaned thread(s)")
        logger.info("")

        if not orphaned_threads:
            logger.info("✓ No orphaned threads found! Database is clean.")
            return

        # Show list of orphaned threads
        logger.info("Orphaned threads:")
        # Show first 10
        for i, thread_id in enumerate(orphaned_threads[:10], 1):
            logger.info(f"  {i}. {thread_id}")

        if len(orphaned_threads) > 10:
            logger.info(f"  ... and {len(orphaned_threads) - 10} more")

        logger.info("")

        if dry_run:
            logger.info("=" * 60)
            logger.warning("DRY RUN MODE - No changes made")
            logger.info("=" * 60)
            logger.info("To actually delete these threads, run:")
            logger.info(
                "  python -m scripts.cleanup_orphaned_threads --execute")
            logger.info("")
            return

        # Confirm deletion
        logger.warning("=" * 60)
        logger.warning(
            f"WARNING: About to DELETE {len(orphaned_threads)} thread(s)")
        logger.warning("This action CANNOT be undone!")
        logger.warning("=" * 60)

        confirmation = input("\nType 'DELETE' to confirm: ")

        if confirmation != "DELETE":
            logger.info("Cancelled by user")
            return

        logger.info("")
        logger.info("Deleting threads...")

        # Delete threads
        success_count = 0
        fail_count = 0

        for i, thread_id in enumerate(orphaned_threads, 1):
            logger.info(
                f"[{i}/{len(orphaned_threads)}] Deleting {thread_id}...")
            success = await delete_thread_checkpoints(checkpointer, thread_id)

            if success:
                success_count += 1
            else:
                fail_count += 1

        # Commit transaction
        await conn.commit()

        logger.info("")
        logger.info("=" * 60)
        logger.info("Cleanup Complete")
        logger.info("=" * 60)
        logger.info(f"✓ Successfully deleted: {success_count} thread(s)")
        if fail_count > 0:
            logger.warning(f"✗ Failed to delete: {fail_count} thread(s)")
        logger.info("")

    except Exception as e:
        logger.error(f"Error during cleanup: {e}", exc_info=True)
        await conn.rollback()
        logger.error("Transaction rolled back")

    finally:
        await conn.close()
        logger.info("Database connection closed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Cleanup orphaned threads without user_id"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete threads (default is dry-run mode)"
    )

    args = parser.parse_args()

    asyncio.run(main(dry_run=not args.execute))
