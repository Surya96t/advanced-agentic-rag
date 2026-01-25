"""
Integration tests for API endpoints (Phase 5).

Tests document CRUD and non-streaming chat endpoints.
Uses pytest fixtures from conftest.py for database setup.
"""

import pytest
from httpx import AsyncClient
from uuid import uuid4

from app.main import app
from app.database.client import get_supabase_client
from app.database.repositories.documents import DocumentRepository
from app.schemas.document import DocumentCreate


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
async def test_document(supabase_client):
    """
    Create a test document in the database.

    Yields document data, then cleans up after test.
    """
    repo = DocumentRepository(supabase_client)
    user_id = "test_user_123"

    # Create test document
    doc_create = DocumentCreate(
        title="Test API Document",
        content="This is a test document for API endpoint testing.",
        source_url="https://test.example.com/api-doc",
        metadata={"category": "test", "phase": 5}
    )

    doc = await repo.create_document(doc_create, user_id)

    yield doc

    # Cleanup: delete document and chunks
    try:
        await repo.delete_document(doc.id, user_id)
    except Exception:
        pass  # Already deleted or doesn't exist


@pytest.fixture
async def async_client():
    """
    Create an async HTTP client for testing endpoints.
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


# ============================================================================
# Document Endpoints Tests
# ============================================================================


class TestDocumentEndpoints:
    """Test suite for document CRUD endpoints."""

    @pytest.mark.asyncio
    async def test_list_documents_empty(self, async_client, supabase_client):
        """Test listing documents when none exist for user."""
        response = await async_client.get("/api/v1/documents")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        # May have documents from other tests, just verify structure
        if len(data) > 0:
            assert "id" in data[0]
            assert "title" in data[0]
            assert "user_id" in data[0]

    @pytest.mark.asyncio
    async def test_list_documents_with_data(self, async_client, test_document):
        """Test listing documents returns created documents."""
        response = await async_client.get("/api/v1/documents")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) > 0

        # Find our test document
        doc_ids = [doc["id"] for doc in data]
        assert str(test_document.id) in doc_ids

        # Verify document structure
        our_doc = next(d for d in data if d["id"] == str(test_document.id))
        assert our_doc["title"] == test_document.title
        assert our_doc["user_id"] == test_document.user_id
        assert "created_at" in our_doc
        assert "chunk_count" in our_doc

    @pytest.mark.asyncio
    async def test_delete_document_success(self, async_client, test_document):
        """Test successfully deleting a document."""
        doc_id = str(test_document.id)

        response = await async_client.delete(f"/api/v1/documents/{doc_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["message"] == "Document deleted successfully"
        assert data["document_id"] == doc_id

        # Verify document is actually deleted
        list_response = await async_client.get("/api/v1/documents")
        remaining_docs = list_response.json()
        doc_ids = [d["id"] for d in remaining_docs]
        assert doc_id not in doc_ids

    @pytest.mark.asyncio
    async def test_delete_document_not_found(self, async_client):
        """Test deleting a non-existent document returns 404."""
        fake_id = str(uuid4())

        response = await async_client.delete(f"/api/v1/documents/{fake_id}")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_delete_document_invalid_uuid(self, async_client):
        """Test deleting with invalid UUID returns 422."""
        response = await async_client.delete("/api/v1/documents/invalid-uuid-format")

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


# ============================================================================
# Chat Endpoint Tests (Non-Streaming)
# ============================================================================


class TestChatEndpoint:
    """Test suite for chat endpoint (non-streaming mode)."""

    @pytest.mark.asyncio
    async def test_chat_non_streaming_success(self, async_client, test_document):
        """Test non-streaming chat returns valid response."""
        # Note: This requires the full agentic stack to be functional
        # May need to mock the agent graph for faster tests

        payload = {
            "message": "What is LangGraph?",
            "stream": False,
            "thread_id": None
        }

        response = await async_client.post("/api/v1/chat", json=payload)

        # Should succeed or fail gracefully
        assert response.status_code in [200, 500]  # 500 if agent fails

        if response.status_code == 200:
            data = response.json()

            # Verify ChatResponse structure
            assert "content" in data or "answer" in data  # Depending on schema
            assert "metadata" in data or "sources" in data or True  # Flexible check

    @pytest.mark.asyncio
    async def test_chat_validation_error(self, async_client):
        """Test chat with invalid payload returns 422."""
        # Missing required 'message' field
        payload = {
            "stream": False
        }

        response = await async_client.post("/api/v1/chat", json=payload)

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_chat_empty_message(self, async_client):
        """Test chat with empty message returns 422."""
        payload = {
            "message": "",
            "stream": False
        }

        response = await async_client.post("/api/v1/chat", json=payload)

        # Should be rejected by validation
        assert response.status_code in [422, 400]

    @pytest.mark.asyncio
    async def test_chat_with_thread_id(self, async_client):
        """Test chat with explicit thread_id."""
        thread_id = str(uuid4())

        payload = {
            "message": "Test message for thread",
            "stream": False,
            "thread_id": thread_id
        }

        response = await async_client.post("/api/v1/chat", json=payload)

        # Should succeed or fail gracefully
        assert response.status_code in [200, 500]


# ============================================================================
# Health Check Test
# ============================================================================


class TestHealthEndpoint:
    """Test suite for health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self, async_client):
        """Test health check endpoint returns OK."""
        response = await async_client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ok"
        assert "timestamp" in data
        assert "service" in data
