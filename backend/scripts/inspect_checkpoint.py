"""Check actual checkpoint structure"""
import asyncio
import json
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

    # Get one checkpoint and inspect its structure
    query = """
    SELECT 
        thread_id,
        checkpoint,
        metadata
    FROM checkpoints
    WHERE checkpoint_ns = ''
    ORDER BY checkpoint_id DESC
    LIMIT 1
    """

    async with conn.cursor() as cur:
        await cur.execute(query)
        row = await cur.fetchone()

        if row:
            print("\n=== Checkpoint Structure ===\n")
            print(f"Thread ID: {row['thread_id']}\n")

            checkpoint = row['checkpoint']
            print("Checkpoint keys:", list(checkpoint.keys()))
            print()

            if 'channel_values' in checkpoint:
                print("channel_values keys:", list(
                    checkpoint['channel_values'].keys()))
                print()

                # Check for messages in different possible locations
                cv = checkpoint['channel_values']
                print(f"Keys in channel_values: {list(cv.keys())}")

                # Print first few keys and their types
                for key in list(cv.keys())[:10]:
                    val = cv[key]
                    print(f"  {key}: {type(val).__name__}")
                    if key == 'messages' or 'message' in key.lower():
                        print(f"    Value: {val}")

    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
