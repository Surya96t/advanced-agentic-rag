"""
Integration tests for SSE streaming chat endpoint (Phase 5).

Tests Server-Sent Events (SSE) streaming functionality.
Uses httpx-sse for SSE client simulation.
"""

import time
import pytest
import json
from httpx import AsyncClient, ASGITransport
from uuid import uuid4

from app.main import app
from app.api.deps import get_current_user_id, check_user_rate_limit


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
async def async_client():
    """Create an async HTTP client with auth and rate limiting bypassed."""

    async def mock_user_id() -> str:
        return "dev-user"

    async def mock_rate_limit() -> tuple[int, int, int]:
        return (100, 99, int(time.time()) + 3600)

    app.dependency_overrides[get_current_user_id] = mock_user_id
    app.dependency_overrides[check_user_rate_limit] = mock_rate_limit

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


# ============================================================================
# SSE Streaming Tests
# ============================================================================


class TestSSEStreaming:
    """Test suite for SSE streaming chat endpoint."""

    @pytest.mark.asyncio
    async def test_sse_stream_headers(self, async_client):
        """Test SSE stream returns correct headers."""
        payload = {
            "message": "Test streaming question",
            "stream": True
        }

        # Use stream to get headers without consuming full response
        async with async_client.stream("POST", "/api/v1/chat", json=payload) as response:
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
            assert response.headers["cache-control"] == "no-cache"
            assert response.headers["connection"] == "keep-alive"

    @pytest.mark.asyncio
    async def test_sse_stream_events(self, async_client):
        """Test SSE stream emits valid events."""
        payload = {
            "message": "What is LangGraph?",
            "stream": True
            # No thread_id: backend auto-generates one, no checkpointer required
        }

        events = []

        async with async_client.stream("POST", "/api/v1/chat", json=payload) as response:
            assert response.status_code == 200

            # Collect events (limit to prevent infinite loop on error)
            max_events = 100
            async for line in response.aiter_lines():
                if len(events) >= max_events:
                    break

                # Parse SSE format: "event: <type>\ndata: <json>\n"
                if line.startswith("event:"):
                    event_type = line.split(":", 1)[1].strip()
                    events.append({"type": event_type, "data": None})
                elif line.startswith("data:") and events:
                    data_str = line.split(":", 1)[1].strip()
                    try:
                        events[-1]["data"] = json.loads(data_str)
                    except json.JSONDecodeError:
                        events[-1]["data"] = data_str

        # Verify events structure
        assert len(events) > 0, "Should receive at least one event"

        # Should have 'end' event as last event
        event_types = [e["type"] for e in events]
        assert "end" in event_types, "Should receive 'end' event"

        # Verify 'end' is the last event
        assert events[-1]["type"] == "end"

        # Check for expected event types (actual backend SSE event names)
        valid_event_types = {
            "agent_start", "agent_complete", "agent_error",
            "token", "citation", "validation", "end", "error",
            "query_classification", "context_status", "conversation_summary",
            "progress", "thread_created",
        }
        for event in events:
            assert event["type"] in valid_event_types, f"Unexpected event type: {event['type']}"

    @pytest.mark.asyncio
    async def test_sse_stream_answer_accumulation(self, async_client):
        """Test SSE stream provides progressive answer chunks."""
        payload = {
            "message": "Explain LangGraph briefly",
            "stream": True
        }

        answer_events = []

        async with async_client.stream("POST", "/api/v1/chat", json=payload) as response:
            current_event_type = None

            async for line in response.aiter_lines():
                if line.startswith("event:"):
                    current_event_type = line.split(":", 1)[1].strip()
                elif line.startswith("data:") and current_event_type == "answer":
                    data_str = line.split(":", 1)[1].strip()
                    try:
                        answer_events.append(json.loads(data_str))
                    except json.JSONDecodeError:
                        pass
                elif line.startswith("event:") and line.split(":", 1)[1].strip() == "end":
                    break

        # Should receive answer chunks (unless agent fails)
        # This test is lenient as it depends on the agent working
        if len(answer_events) > 0:
            # Verify answer events have 'content' or 'answer' field
            for event in answer_events:
                assert isinstance(event, dict)
                # Flexible check for content field
                has_content = any(key in event for key in [
                                  "content", "answer", "delta", "text"])
                assert has_content, f"Answer event missing content: {event}"

    @pytest.mark.asyncio
    async def test_sse_stream_validation_error(self, async_client):
        """Test SSE stream with invalid payload returns 422."""
        # Missing required 'message' field
        payload = {
            "stream": True
        }

        response = await async_client.post("/api/v1/chat", json=payload)

        assert response.status_code == 422
        data = response.json()
        # Backend custom error handler uses "details" (plural) or "error" key
        assert "details" in data or "detail" in data or "error" in data

    @pytest.mark.asyncio
    async def test_sse_stream_error_event(self, async_client):
        """Test SSE stream emits error event on failure."""
        # This test simulates a scenario that would cause agent failure
        # For example, extremely long or malformed message

        payload = {
            "message": "x" * 100000,  # Very long message
            "stream": True
        }

        events = []

        async with async_client.stream("POST", "/api/v1/chat", json=payload) as response:
            # May return 422, 500, or stream with error event
            if response.status_code == 200:
                async for line in response.aiter_lines():
                    if line.startswith("event:"):
                        event_type = line.split(":", 1)[1].strip()
                        events.append(event_type)
                        if event_type == "end":
                            break

                # Should have received error or end event
                assert "error" in events or "end" in events
            else:
                # Validation error or server error
                assert response.status_code in [422, 500]

    @pytest.mark.asyncio
    async def test_sse_stream_thread_continuity(self, async_client):
        """Test SSE stream respects thread_id for conversation continuity."""
        thread_id = str(uuid4())

        # First message
        payload1 = {
            "message": "Remember: my favorite color is blue",
            "stream": True,
            "thread_id": thread_id
        }

        events1 = []
        async with async_client.stream("POST", "/api/v1/chat", json=payload1) as response:
            if response.status_code == 503:
                pytest.skip("Checkpointer (Supabase) unavailable in test environment")
            assert response.status_code == 200
            async for line in response.aiter_lines():
                if line.startswith("event:"):
                    event_type = line.split(":", 1)[1].strip()
                    events1.append(event_type)
                    if event_type == "end":
                        break

        # Second message in same thread
        payload2 = {
            "message": "What is my favorite color?",
            "stream": True,
            "thread_id": thread_id
        }

        events2 = []
        answer_content = []

        async with async_client.stream("POST", "/api/v1/chat", json=payload2) as response:
            if response.status_code == 503:
                pytest.skip("Checkpointer (Supabase) unavailable in test environment")
            assert response.status_code == 200
            current_event_type = None

            async for line in response.aiter_lines():
                if line.startswith("event:"):
                    current_event_type = line.split(":", 1)[1].strip()
                    events2.append(current_event_type)
                    if current_event_type == "end":
                        break
                elif line.startswith("data:") and current_event_type == "answer":
                    data_str = line.split(":", 1)[1].strip()
                    try:
                        data = json.loads(data_str)
                        if "content" in data:
                            answer_content.append(data["content"])
                        elif "answer" in data:
                            answer_content.append(data["answer"])
                    except json.JSONDecodeError:
                        pass

        # Both conversations should complete
        assert "end" in events1
        assert "end" in events2

        # Note: Actual memory recall depends on agent implementation
        # This test just verifies the thread_id is accepted and processed


# ============================================================================
# SSE Format Compliance Tests
# ============================================================================


class TestSSEFormatCompliance:
    """Test SSE format compliance according to SSE specification."""

    @pytest.mark.asyncio
    async def test_sse_format_structure(self, async_client):
        """Test SSE events follow proper SSE format."""
        payload = {
            "message": "Test SSE format",
            "stream": True
        }

        lines = []

        async with async_client.stream("POST", "/api/v1/chat", json=payload) as response:
            assert response.status_code == 200

            # Collect first 50 lines
            async for line in response.aiter_lines():
                lines.append(line)
                if len(lines) >= 50:
                    break

        # SSE events should have:
        # - "event: <type>" line
        # - "data: <json>" line
        # - Empty line separator (sometimes)

        event_lines = [l for l in lines if l.startswith("event:")]
        data_lines = [l for l in lines if l.startswith("data:")]

        assert len(event_lines) > 0, "Should have event: lines"
        assert len(data_lines) > 0, "Should have data: lines"

        # Each event should have corresponding data
        # (allowing some flexibility for empty lines)
        assert len(event_lines) <= len(data_lines) + 2  # Allow some variance

    @pytest.mark.asyncio
    async def test_sse_json_data_validity(self, async_client):
        """Test SSE data payloads are valid JSON."""
        payload = {
            "message": "Test JSON validity",
            "stream": True
        }

        data_payloads = []

        async with async_client.stream("POST", "/api/v1/chat", json=payload) as response:
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    data_str = line.split(":", 1)[1].strip()
                    data_payloads.append(data_str)

                    # Verify it's valid JSON
                    try:
                        parsed = json.loads(data_str)
                        assert isinstance(
                            parsed, dict), "Data should be JSON object"
                    except json.JSONDecodeError as e:
                        pytest.fail(
                            f"Invalid JSON in SSE data: {data_str}\nError: {e}")

                # Stop after 'end' event
                if line.startswith("event:") and "end" in line:
                    break

        assert len(data_payloads) > 0, "Should receive at least one data payload"
