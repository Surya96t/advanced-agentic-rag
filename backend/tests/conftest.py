"""
Pytest fixtures and configuration for integration tests.

This module provides shared fixtures for testing the RAG system,
including database connections, embedders, search components, and test data.
"""

import asyncio
import os
from pathlib import Path
from typing import AsyncGenerator, Generator
from uuid import UUID

import pytest
import pytest_asyncio
from supabase import Client, create_client

from app.core.config import settings
from app.database.repositories.chunks import ChunkRepository
from app.database.repositories.documents import DocumentRepository
from app.ingestion.embeddings import EmbeddingClient
from app.ingestion.pipeline import IngestionPipeline
from app.retrieval.hybrid_search import HybridSearcher
from app.retrieval.rerankers.flashrank import FlashRankReranker
from app.retrieval.text_search import TextSearcher
from app.retrieval.vector_search import VectorSearcher
from app.utils.logger import get_logger

logger = get_logger(__name__)


@pytest.fixture(scope="session")
def event_loop():
    """
    Create an event loop for the test session.

    This ensures async tests can run properly.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_user_id(supabase_client: Client) -> Generator[str, None, None]:
    """
    Provide a consistent test user ID and create user in database.

    Creates a test user before tests and cleans up after.

    Yields:
        Test user ID string
    """
    user_id = "test_user_integration_123"

    # Create test user
    try:
        supabase_client.table("users").insert({
            "id": user_id,
            "email": f"{user_id}@test.com",
        }).execute()
        logger.info(f"Created test user: {user_id}")
    except Exception as e:
        # User might already exist, that's okay
        logger.warning(f"Test user may already exist: {e}")

    yield user_id

    # Cleanup: Delete test user's documents and chunks
    try:
        # Delete chunks first (FK constraint)
        supabase_client.table("document_chunks").delete().eq(
            "user_id", user_id
        ).execute()

        # Delete documents
        supabase_client.table("documents").delete().eq(
            "user_id", user_id
        ).execute()

        # Delete user
        supabase_client.table("users").delete().eq(
            "id", user_id
        ).execute()

        logger.info(f"Cleaned up test user: {user_id}")
    except Exception as e:
        logger.warning(f"Failed to cleanup test user: {e}")


@pytest.fixture(scope="session")
def supabase_client() -> Client:
    """
    Create Supabase client for testing.

    Uses service role key to bypass RLS for test setup/teardown.

    Returns:
        Supabase client instance
    """
    client = create_client(
        supabase_url=settings.supabase_url,
        supabase_key=settings.supabase_service_key,
    )
    return client


@pytest_asyncio.fixture(scope="session")
async def embedder() -> EmbeddingClient:
    """
    Create OpenAI embedding client for testing.

    Returns:
        EmbeddingClient instance (reads API key from settings)
    """
    return EmbeddingClient(
        model=settings.openai_embedding_model,
        dimensions=settings.openai_embedding_dimensions,
    )


@pytest_asyncio.fixture(scope="session")
async def vector_searcher(
    supabase_client: Client,
    embedder: EmbeddingClient,
) -> VectorSearcher:
    """
    Create VectorSearcher instance for testing.

    Args:
        supabase_client: Supabase client
        embedder: Embedding client

    Returns:
        VectorSearcher instance
    """
    return VectorSearcher(db=supabase_client, embedder=embedder)


@pytest_asyncio.fixture(scope="session")
async def text_searcher(supabase_client: Client) -> TextSearcher:
    """
    Create TextSearcher instance for testing.

    Args:
        supabase_client: Supabase client

    Returns:
        TextSearcher instance
    """
    return TextSearcher(db=supabase_client)


@pytest_asyncio.fixture(scope="session")
async def hybrid_searcher(
    supabase_client: Client,
    embedder: EmbeddingClient,
) -> HybridSearcher:
    """
    Create HybridSearcher instance for testing.

    Args:
        supabase_client: Supabase client
        embedder: Embedding client

    Returns:
        HybridSearcher instance
    """
    return HybridSearcher(
        db=supabase_client,
        embedder=embedder,
    )


@pytest_asyncio.fixture(scope="session")
async def flashrank_reranker() -> FlashRankReranker:
    """
    Create FlashRankReranker instance for testing.

    Uses the smallest/fastest model for testing.

    Returns:
        FlashRankReranker instance
    """
    return FlashRankReranker(model_name="ms-marco-TinyBERT-L-2-v2")


@pytest_asyncio.fixture(scope="function")
async def ingestion_pipeline(
    supabase_client: Client,
    embedder: EmbeddingClient,
) -> IngestionPipeline:
    """
    Create IngestionPipeline instance for testing.

    Args:
        supabase_client: Supabase client
        embedder: Embedding client

    Returns:
        IngestionPipeline instance
    """
    # Create repositories
    doc_repo = DocumentRepository(supabase_client)
    chunk_repo = ChunkRepository(supabase_client)

    return IngestionPipeline(
        doc_repo=doc_repo,
        chunk_repo=chunk_repo,
        embedding_client=embedder,
    )


@pytest_asyncio.fixture(scope="function")
async def test_documents(
    ingestion_pipeline: IngestionPipeline,
    supabase_client: Client,
    test_user_id: str,
) -> AsyncGenerator[list[UUID], None]:
    """
    Ingest test documents and provide document IDs.

    This fixture:
    1. Ingests test documents from backend/data/
    2. Yields document IDs for use in tests
    3. Cleans up documents after test completes

    Args:
        ingestion_pipeline: Pipeline for ingesting documents
        supabase_client: Supabase client for cleanup
        test_user_id: Test user ID

    Yields:
        List of document IDs
    """
    # Get actual Convex documentation from data/raw/convex/
    data_dir = Path(__file__).parent.parent.parent / "data" / "raw" / "convex"
    test_files = [
        data_dir / "mutations.md",
    ]

    # Verify test files exist
    for file_path in test_files:
        if not file_path.exists():
            raise FileNotFoundError(
                f"Test file not found: {file_path}. "
                "Ensure mutations.md exists in data/raw/convex/"
            )

    document_ids: list[UUID] = []

    # Clean up any existing test documents with same title first
    # (may exist from previous test runs with different user IDs)
    for file_path in test_files:
        # Delete any existing documents with this title
        existing_docs = (
            supabase_client.table("documents")
            .select("id")
            .eq("title", file_path.name)
            .execute()
        )

        for doc in existing_docs.data:
            doc_id = doc["id"]
            # Delete chunks first (FK constraint)
            supabase_client.table("document_chunks").delete().eq(
                "document_id", doc_id
            ).execute()
            # Delete document
            supabase_client.table("documents").delete().eq(
                "id", doc_id
            ).execute()

    # Ingest each test file
    for file_path in test_files:
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        result = await ingestion_pipeline.ingest_document(
            file_bytes=file_bytes,
            filename=file_path.name,
            user_id=test_user_id,
            metadata={"test": True, "source": str(file_path)},
        )

        document_ids.append(result.id)

    # Yield document IDs for tests
    yield document_ids

    # Cleanup: Delete test documents and chunks
    for doc_id in document_ids:
        # Delete chunks first (FK constraint)
        supabase_client.table("document_chunks").delete().eq(
            "document_id", str(doc_id)
        ).execute()

        # Delete document
        supabase_client.table("documents").delete().eq(
            "id", str(doc_id)
        ).execute()


@pytest.fixture(scope="session")
def test_queries() -> dict[str, str]:
    """
    Provide a set of test queries for different scenarios.

    These queries are designed to match content in the test documents
    (mutations.md and test files).

    Returns:
        Dictionary mapping query types to query strings
    """
    return {
        "semantic": "How do I write data to the database using mutations?",
        "keyword": "mutation handler database insert tasks",
        "technical": "mutation constructor function handler",
        "phrase": '"mutation constructor"',
        "no_match": "quantum computing blockchain AI unicorns",
    }
