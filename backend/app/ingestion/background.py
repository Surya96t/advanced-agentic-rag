"""
Celery background worker for document ingestion.

Moves the heavy parse → chunk → embed → store pipeline off the HTTP request
thread.  The FastAPI endpoint uploads the file to Supabase Storage and then
dispatches this task, returning 202 immediately to the frontend.

Worker startup (from backend/):
    celery -A app.ingestion.background worker --loglevel=info

Design notes:
- File bytes are base64-encoded for JSON-safe transport over the Redis broker.
- Each task builds its own DB / embedding clients so that Celery worker
  processes never share asyncio event loops or connection pools with the web
  process.
- asyncio.run() bridges the sync Celery task boundary into the async pipeline.
"""

import asyncio
import base64

from celery import Celery

from app.core.config import settings
from app.utils.errors import (
    AuthenticationError,
    AuthorizationError,
    ChunkingError,
    ConflictError,
    DatabaseError,
    DocumentProcessingError,
    EmbeddingError,
    ExternalServiceError,
    NotFoundError,
    ValidationError,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Transient error detection
# ---------------------------------------------------------------------------

# Errors that will never succeed on retry — fail immediately.
_PERMANENT_ERRORS = (
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ConflictError,
    ChunkingError,
    DocumentProcessingError,
)

# Errors that may succeed on retry (network blips, 5xx, temporary service issues).
_TRANSIENT_ERRORS = (
    DatabaseError,
    ExternalServiceError,
    EmbeddingError,
)


def _is_transient(exc: BaseException) -> bool:
    """
    Return True if *exc* is likely transient and worth retrying.

    Matches our app-level transient error types plus common network /
    timeout exceptions from httpx and the standard library.
    """
    if isinstance(exc, _PERMANENT_ERRORS):
        return False
    if isinstance(exc, _TRANSIENT_ERRORS):
        return True
    # Network / timeout errors from httpx (used by openai SDK) and stdlib
    try:
        import httpx
        if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError)):
            return True
    except ImportError:
        pass
    import socket
    if isinstance(exc, (TimeoutError, ConnectionError, socket.timeout, OSError)):
        return True
    return False


# ---------------------------------------------------------------------------
# Celery application
# ---------------------------------------------------------------------------

celery_app = Celery(
    "integration_forge",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    # Keep results for 1 hour so status polling always finds them
    result_expires=3600,
    # Serialize tasks as JSON (safe, human-readable)
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Acknowledge the task only after it finishes (safer for idempotency)
    task_acks_late=True,
    # Re-queue on worker crash, not on normal failure
    task_reject_on_worker_lost=True,
    # Timezone
    timezone="UTC",
    enable_utc=True,
)


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------


@celery_app.task(
    bind=True,
    name="app.ingestion.background.ingest_document_task",
    max_retries=2,
    default_retry_delay=10,
    track_started=True,
)
def ingest_document_task(
    self,  # noqa: ANN001 – bound task instance
    file_bytes_b64: str,
    filename: str,
    user_id: str,
    storage_path: str | None,
) -> dict:
    """
    Process a document through the full ingestion pipeline.

    Args:
        file_bytes_b64: Base64-encoded raw file bytes.
        filename: Original filename (used for parsing and deduplication).
        user_id: Clerk user ID of the uploading user.
        storage_path: Path already uploaded to Supabase Storage
                      (passed through to pipeline for blob_path metadata).

    Returns:
        dict with keys: document_id, status, is_duplicate

    Raises:
        Retries up to max_retries times on transient failures before failing.
    """
    logger.info(
        "Celery task started",
        task_id=self.request.id,
        filename=filename,
        user_id=user_id,
    )

    async def _run() -> dict:
        # Late imports — keep module load fast and avoid circular imports at
        # worker startup time.
        from app.database.client import SupabaseClient
        from app.database.repositories.chunks import ChunkRepository
        from app.database.repositories.documents import DocumentRepository
        from app.ingestion.embeddings import get_embedding_client
        from app.ingestion.pipeline import IngestionPipeline
        from app.core import cache as response_cache

        db = SupabaseClient.get_client()
        doc_repo = DocumentRepository(db)
        chunk_repo = ChunkRepository(db)
        embedding_client = await get_embedding_client()

        pipeline = IngestionPipeline(
            doc_repo=doc_repo,
            chunk_repo=chunk_repo,
            embedding_client=embedding_client,
        )

        file_bytes = base64.b64decode(file_bytes_b64)

        document, is_duplicate = await pipeline.ingest_document(
            file_bytes=file_bytes,
            filename=filename,
            user_id=user_id,
            metadata={"document_title": filename},
            storage_path=storage_path,
        )

        # Invalidate cached responses so the user sees their new document
        await response_cache.invalidate_user(user_id)

        logger.info(
            "Celery task completed",
            task_id=self.request.id,
            document_id=str(document.id),
            is_duplicate=is_duplicate,
        )

        return {
            "document_id": str(document.id),
            "status": document.status.value,
            "is_duplicate": is_duplicate,
        }

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.error(
            "Celery task failed",
            task_id=self.request.id,
            filename=filename,
            error=str(exc),
            exc_info=True,
        )
        if _is_transient(exc):
            raise self.retry(exc=exc)
        # Permanent error — fail immediately without consuming retry budget
        raise
