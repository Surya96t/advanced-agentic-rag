#!/usr/bin/env python3
"""
Test if the agentic RAG workflow emits citations correctly
"""
import structlog
from app.schemas.chat import ChatRequest
from app.agents.graph import get_graph
import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


logger = structlog.get_logger()


async def test_citation_emission():
    """Test that citations are emitted in the agent workflow"""
    logger.info("Testing citation emission in agentic RAG workflow...")

    # Get the compiled graph
    graph = get_graph()

    # Create a test request
    test_request = ChatRequest(
        question="What is LangGraph?",
        user_id="test_user",
        conversation_history=[]
    )

    # Convert to graph input
    input_state = {
        "question": test_request.question,
        "user_id": test_request.user_id,
        "conversation_history": test_request.conversation_history,
    }

    logger.info("Invoking agent graph...")

    # Collect all events
    events = []
    citations_found = False

    async for event in graph.astream_events(input_state, version="v2"):
        events.append(event)

        # Check for citation events
        if event.get("event") == "on_custom_event":
            if event.get("name") == "citation":
                logger.info(f"✅ CITATION EVENT FOUND", data=event.get("data"))
                citations_found = True

    logger.info(f"Total events: {len(events)}")
    logger.info(f"Citations found: {citations_found}")

    if citations_found:
        logger.info("✅ Citation emission is working!")
    else:
        logger.warning("⚠️  No citations were emitted - this could mean:")
        logger.warning("   1. No relevant chunks were found for the query")
        logger.warning("   2. The retriever node didn't emit citations")
        logger.warning("   3. Check backend logs for errors")


if __name__ == "__main__":
    asyncio.run(test_citation_emission())
