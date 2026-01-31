#!/usr/bin/env python3
"""
Test script to verify token-by-token streaming from the generator node.

This script tests the new streaming implementation by:
1. Starting the agent with a simple query
2. Streaming the response with custom token events
3. Displaying each token as it arrives
4. Verifying timing and performance

Usage:
    python scripts/test_token_streaming.py
"""

from app.utils.logger import get_logger
from app.core.config import settings
from app.agents.graph import stream_agent
import asyncio
import json
import sys
import time
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


logger = get_logger(__name__)


async def test_token_streaming():
    """Test token-by-token streaming functionality."""
    print("=" * 80)
    print("TOKEN-BY-TOKEN STREAMING TEST")
    print("=" * 80)
    print(f"OpenAI Model: {settings.openai_model}")
    print(f"Test Query: 'What is Clerk?'")
    print("=" * 80)
    print()

    # Simple query to test streaming
    query = "What is Clerk?"

    # Track timing and tokens
    start_time = time.time()
    first_token_time = None
    token_count = 0
    tokens = []

    print("Starting stream...")
    print("-" * 80)

    try:
        async for event in stream_agent(query=query):
            event_type = event.get("event")
            data_json = event.get("data", "{}")

            # Parse data
            try:
                data = json.loads(data_json)
            except json.JSONDecodeError:
                data = {}

            # Handle different event types
            if event_type == "agent_start":
                agent = data.get("agent", "unknown")
                message = data.get("message", "")
                print(f"\n[{agent.upper()}] {message}")

            elif event_type == "agent_complete":
                agent = data.get("agent", "unknown")
                print(f"[{agent.upper()}] Complete")

            elif event_type == "token":
                # This is the key event - individual tokens!
                token = data.get("token", "")
                model = data.get("model", "")

                # Track first token time
                if first_token_time is None:
                    first_token_time = time.time()
                    time_to_first_token = first_token_time - start_time
                    print(
                        f"\n⚡ FIRST TOKEN received in {time_to_first_token:.3f}s")
                    print(f"Model: {model}")
                    print("-" * 80)
                    print("STREAMING RESPONSE:")
                    print()

                # Print token (no newline)
                print(token, end="", flush=True)
                token_count += 1
                tokens.append(token)

            elif event_type == "citation":
                # Don't print citations during streaming to keep output clean
                pass

            elif event_type == "validation":
                passed = data.get("passed", False)
                score = data.get("score", 0.0)
                print(
                    f"\n[VALIDATION] {'✓ Passed' if passed else '✗ Failed'} (score: {score:.2f})")

            elif event_type == "end":
                success = data.get("success", False)
                error = data.get("error")
                thread_id = data.get("thread_id", "unknown")

                print("\n")
                print("-" * 80)
                print(f"\n[END] {'✓ Success' if success else '✗ Failed'}")
                if error:
                    print(f"Error: {error}")
                print(f"Thread ID: {thread_id}")

    except Exception as e:
        logger.error(f"Streaming test failed: {e}", exc_info=True)
        print(f"\n✗ ERROR: {e}")
        return False

    # Calculate final stats
    end_time = time.time()
    total_time = end_time - start_time

    # Display results
    print("\n")
    print("=" * 80)
    print("STREAMING TEST RESULTS")
    print("=" * 80)
    print(f"Total Time: {total_time:.3f}s")

    if first_token_time:
        time_to_first_token = first_token_time - start_time
        print(f"Time to First Token: {time_to_first_token:.3f}s")

        if token_count > 0:
            streaming_time = end_time - first_token_time
            tokens_per_second = token_count / streaming_time if streaming_time > 0 else 0
            print(f"Tokens Streamed: {token_count}")
            print(f"Streaming Duration: {streaming_time:.3f}s")
            print(f"Tokens/Second: {tokens_per_second:.1f}")

            # Verify tokens
            full_response = "".join(tokens)
            print(f"Response Length: {len(full_response)} characters")

            # Success if we got tokens
            print()
            print("✓ Token-by-token streaming SUCCESSFUL!")
            return True
        else:
            print("\n✗ No tokens received during streaming")
            return False
    else:
        print("\n✗ No tokens received at all")
        return False


async def main():
    """Run the streaming test."""
    try:
        success = await test_token_streaming()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test failed with exception: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
