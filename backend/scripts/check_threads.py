"""Quick script to check threads in database"""
import asyncio
import psycopg
from psycopg.rows import dict_row
from app.core.config import settings


async def main():
    conn = await psycopg.AsyncConnection.connect(
        settings.supabase_connection_string,
        autocommit=True,
        prepare_threshold=0,
        row_factory=dict_row
    )

    # Check all threads
    query = """
    SELECT 
        thread_id,
        checkpoint->'channel_values'->>'user_id' as user_id,
        jsonb_array_length(checkpoint->'channel_values'->'messages') as message_count,
        checkpoint_id,
        checkpoint->'channel_values'->'messages'->0->>'content' as first_message
    FROM checkpoints
    WHERE checkpoint_ns = ''
    ORDER BY checkpoint_id DESC
    LIMIT 20
    """

    async with conn.cursor() as cur:
        await cur.execute(query)
        rows = await cur.fetchall()

        print(f"\n=== Found {len(rows)} checkpoints ===\n")
        for i, row in enumerate(rows, 1):
            print(f"{i}. Thread: {row['thread_id']}")
            print(f"   User: {row['user_id']}")
            print(f"   Messages: {row['message_count']}")
            print(
                f"   First msg: {row['first_message'][:50] if row['first_message'] else 'None'}...")
            print()

    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
