"""
Script to ingest test documents into the database.

This script ingests the Convex mutations.md documentation
for testing and development purposes.

Usage:
    uv run python scripts/ingest_test_data.py
"""

from app.utils.logger import get_logger
from app.ingestion.pipeline import IngestionPipeline
from app.ingestion.embeddings import EmbeddingClient
from app.database.repositories.documents import DocumentRepository
from app.database.repositories.chunks import ChunkRepository
from app.database.client import SupabaseClient
from app.core.config import settings
import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
# This must be done BEFORE importing from app.* modules
sys.path.insert(0, str(Path(__file__).parent.parent))


logger = get_logger(__name__)

# Test user ID (same as used in tests)
TEST_USER_ID = "test_user_integration_123"


async def create_test_user(db) -> None:
    """
    Create test user in database if it doesn't exist.

    Args:
        db: Supabase client instance
    """
    logger.info(f"Checking if test user exists: {TEST_USER_ID}")

    try:
        # Check if user exists
        result = db.table("users").select(
            "id").eq("id", TEST_USER_ID).execute()

        if result.data:
            logger.info(f"Test user already exists: {TEST_USER_ID}")
            return

        # Create user
        db.table("users").insert({
            "id": TEST_USER_ID,
            "email": f"{TEST_USER_ID}@test.com",
        }).execute()

        logger.info(f"✅ Created test user: {TEST_USER_ID}")

    except Exception as e:
        logger.error(f"Failed to create test user: {e}")
        raise


async def ingest_file(pipeline: IngestionPipeline, file_path: Path) -> None:
    """
    Ingest a single file into the database.

    Args:
        pipeline: Ingestion pipeline instance
        file_path: Path to file to ingest
    """
    logger.info(f"Ingesting file: {file_path.name}")

    try:
        # Read file
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        # Ingest document
        result = await pipeline.ingest_document(
            file_bytes=file_bytes,
            filename=file_path.name,
            user_id=TEST_USER_ID,
            metadata={
                "source": str(file_path),
                "category": "documentation",
                "framework": "convex",
            },
        )

        logger.info(
            f"✅ Successfully ingested {file_path.name}",
            document_id=str(result.id),
            total_chunks=result.chunk_count,
        )

    except Exception as e:
        logger.error(f"❌ Failed to ingest {file_path.name}: {e}")
        raise


async def main():
    """Main ingestion workflow."""
    logger.info("🚀 Starting test data ingestion")
    logger.info(f"Supabase URL: {settings.supabase_url}")
    logger.info(f"Test User ID: {TEST_USER_ID}")

    # Initialize clients
    logger.info("Initializing clients...")
    db = SupabaseClient.get_client()
    embedder = EmbeddingClient()

    # Create repositories
    doc_repo = DocumentRepository(db)
    chunk_repo = ChunkRepository(db)

    # Create ingestion pipeline
    pipeline = IngestionPipeline(
        doc_repo=doc_repo,
        chunk_repo=chunk_repo,
        embedding_client=embedder,
    )

    # Create test user
    await create_test_user(db)

    # Define files to ingest
    data_dir = Path(__file__).parent.parent.parent / "data" / "raw" / "convex"
    files_to_ingest = [
        data_dir / "mutations.md",
        # Add more files here as needed
        # data_dir / "queries.md",
    ]

    # Verify files exist
    for file_path in files_to_ingest:
        if not file_path.exists():
            logger.error(f"❌ File not found: {file_path}")
            logger.info("Available files in directory:")
            if data_dir.exists():
                for f in data_dir.iterdir():
                    logger.info(f"  - {f.name}")
            sys.exit(1)

    # Ingest each file
    logger.info(f"Ingesting {len(files_to_ingest)} file(s)...")
    for file_path in files_to_ingest:
        await ingest_file(pipeline, file_path)

    logger.info("✅ Ingestion complete!")
    logger.info(f"📊 Total documents ingested: {len(files_to_ingest)}")
    logger.info(f"🔑 User ID: {TEST_USER_ID}")
    logger.info("\n🎯 You can now query the RAG system in LangGraph Studio!")


if __name__ == "__main__":
    asyncio.run(main())
