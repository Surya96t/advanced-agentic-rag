"""
Document ingestion API endpoint for Integration Forge.

This endpoint handles document upload and triggers the ingestion pipeline.

Workflow:
1. User uploads a file via POST /api/v1/ingest
2. Validate file type and size
3. Read file content
4. Call IngestionPipeline to process the document
5. Return document record with status

Learning Note:
Why separate upload from processing?
1. Quick response: Return immediately with status=PROCESSING
2. Async processing: Heavy work (embedding, chunking) happens in background
3. User feedback: Frontend can poll status endpoint for progress
4. Scalability: Can queue uploads if processing is slow

For now, we process synchronously to keep it simple.
"""

import base64
import mimetypes
import re
from pathlib import Path
from typing import Annotated

from celery.result import AsyncResult
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)

from app.api.deps import RateLimitInfo, UserID
from app.core.cache import _get_redis
from app.core.storage import (
    StorageClient,
    StorageDeleteError,
    StorageUploadError,
    get_storage_client,
)
from app.ingestion.background import celery_app, ingest_document_task
from app.schemas.document import (
    MAX_FILE_SIZE_BYTES,
    get_file_extension_error_message,
    get_file_size_error_message,
    validate_file_extension,
    validate_file_size,
)
from app.utils.errors import ValidationError
from app.utils.logger import get_logger

# TTL must mirror celery_app result_expires so both expire together
_TASK_DISPATCH_TTL = 3600  # seconds
_TASK_DISPATCH_KEY_PREFIX = "task:dispatched:"

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/api/v1", tags=["ingestion"])


# ============================================================================
# DEPENDENCIES
# ============================================================================


def get_storage() -> StorageClient:
    """Get the application-wide StorageClient instance."""
    return get_storage_client()


# ============================================================================
# ROUTES
# ============================================================================


@router.post(
    "/ingest",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload and ingest a document",
    description=(
        "Upload a document file for ingestion. "
        "Supported formats: Markdown (.md), PDF (.pdf), Text (.txt). "
        "Maximum file size: 10MB. "
        "Returns 202 immediately; poll GET /api/v1/ingest/status/{task_id} for progress."
    ),
    responses={
        202: {
            "description": "Document accepted for background processing",
            "content": {
                "application/json": {"example": {"task_id": "abc123", "status": "processing"}}
            },
        },
        400: {
            "description": "Invalid file type or size",
        },
        413: {
            "description": "File too large",
        },
        500: {
            "description": "Internal server error during processing",
        },
    },
)
async def ingest_document(
    file: Annotated[
        UploadFile,
        File(
            description="Document file to upload (.md, .pdf, or .txt)",
            media_type="multipart/form-data",
        ),
    ],
    user_id: UserID,
    rate_limit_info: RateLimitInfo,
    request: Request,
    response: Response,
    storage: StorageClient = Depends(get_storage),
) -> dict:
    """
    Upload and ingest a document asynchronously.

    This endpoint handles the initial upload steps synchronously, then
    dispatches the heavy processing work to a Celery background worker:
    1. Validate file type and size
    2. Upload raw file to Supabase Storage
    3. Dispatch Celery task for parsing, chunking, embedding, and storage

    Poll GET /api/v1/ingest/status/{task_id} to track progress.

    Args:
        file: Uploaded file (multipart/form-data)
        user_id: Authenticated user ID (from JWT via Clerk)

    Returns:
        202 Accepted with task_id and initial status "processing"

    Raises:
        ValidationError: If file type or size is invalid
        HTTPException: If the upload or task dispatch fails

    Example cURL:
        ```bash
        curl -X POST "http://localhost:8000/api/v1/ingest" \\
             -H "Authorization: Bearer <token>" \\
             -F "file=@/path/to/document.pdf"
        ```

    Example Response:
        ```json
        {
            "task_id": "abc123-def456-...",
            "status": "processing"
        }
        ```
    """
    limit, remaining, reset_time = rate_limit_info
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(reset_time)

    logger.info(
        "Document ingestion requested",
        filename=file.filename,
        content_type=file.content_type,
        user_id=user_id,
    )

    # ========================================================================
    # STEP 1: Validate file
    # ========================================================================

    if not file.filename:
        raise ValidationError(
            message="Filename is required",
            details={"filename": None},
        )

    # Validate file extension
    if not validate_file_extension(file.filename):
        logger.warning(
            "Invalid file extension",
            filename=file.filename,
            user_id=user_id,
        )
        raise ValidationError(
            message=get_file_extension_error_message(),
            details={"filename": file.filename},
        )

    # ========================================================================
    # STEP 2: Validate file size BEFORE reading into memory
    # ========================================================================
    # Security Note: Check file size before reading to prevent OOM attacks
    # Try multiple methods to get file size without loading full content

    file_size: int | None = None

    # Method 1: Check file.size attribute (FastAPI/Starlette provides this)
    if hasattr(file, "size") and file.size is not None:
        file_size = file.size
        logger.debug(
            "File size from file.size attribute",
            filename=file.filename,
            size_bytes=file_size,
        )

    # Method 2: If size is available, validate before reading
    if file_size is not None:
        if not validate_file_size(file_size):
            logger.warning(
                "File size exceeds limit (pre-read check)",
                filename=file.filename,
                size_bytes=file_size,
                user_id=user_id,
            )
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=get_file_size_error_message(),
            )

    # ========================================================================
    # STEP 3: Read file content with streaming validation
    # ========================================================================
    # If size wasn't available, read in chunks and validate as we go

    try:
        if file_size is not None:
            # Size already validated, safe to read
            file_content = await file.read()
            actual_size = len(file_content)

            # Double-check actual size matches reported size
            if actual_size != file_size:
                logger.warning(
                    "Actual file size differs from reported size",
                    filename=file.filename,
                    reported_size=file_size,
                    actual_size=actual_size,
                )

            # Validate actual size (defense in depth)
            if not validate_file_size(actual_size):
                logger.warning(
                    "File size exceeds limit (post-read check)",
                    filename=file.filename,
                    size_bytes=actual_size,
                    user_id=user_id,
                )
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=get_file_size_error_message(),
                )
        else:
            # Size unknown, read in chunks with limit enforcement
            logger.debug(
                "Streaming file read (size unknown)",
                filename=file.filename,
            )

            chunks = []
            total_size = 0
            chunk_size = 1024 * 1024  # 1MB chunks

            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break

                total_size += len(chunk)

                # Check if we've exceeded the limit
                if total_size > MAX_FILE_SIZE_BYTES:
                    logger.warning(
                        "File size exceeds limit (streaming check)",
                        filename=file.filename,
                        size_bytes=total_size,
                        user_id=user_id,
                    )
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=get_file_size_error_message(),
                    )

                chunks.append(chunk)

            file_content = b"".join(chunks)
            actual_size = len(file_content)

            logger.debug(
                "Streaming read completed",
                filename=file.filename,
                size_bytes=actual_size,
            )

    except HTTPException:
        # Re-raise HTTP exceptions (file too large)
        raise
    except Exception as e:
        logger.error(
            "Failed to read uploaded file",
            filename=file.filename,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to read uploaded file",
        )

    logger.info(
        "File validation passed",
        filename=file.filename,
        size_bytes=len(file_content),
        user_id=user_id,
    )

    # ========================================================================
    # STEP 4: Upload file to storage
    # ========================================================================

    storage_path: str | None = None
    try:
        import uuid as _uuid

        # Temporary document ID used to build the storage path.
        # The real document UUID is generated by the pipeline (Pydantic default),
        # so we give the file a deterministic prefix based on the user / filename
        # and replace with the actual document ID after creation in pipeline.
        # For now we generate a new UUID here — the pipeline does not yet expose
        # the document ID before record creation, so we store the file first.
        doc_upload_id = _uuid.uuid4()
        # Sanitize filename: strip directory components, remove unsafe characters,
        # drop null bytes, and truncate to a safe length to prevent path traversal.
        raw_name = file.filename or "file"
        # Take only the final path component to strip any directory traversal
        raw_name = Path(raw_name).name
        # Remove null bytes and path separators
        raw_name = raw_name.replace("\x00", "").replace("/", "").replace("\\", "")
        # Keep only alphanumerics, dots, dashes, and underscores
        raw_name = re.sub(r"[^\w.\-]", "_", raw_name)
        # Truncate to 255 characters (common filesystem limit)
        safe_filename = raw_name[:255] or "file"
        storage_path = f"{user_id}/{doc_upload_id}/{safe_filename}"

        # Derive the MIME type from the filename extension when the
        # multipart field carries a generic or absent content-type.
        # Supabase Storage rejects "application/octet-stream", so we fall
        # back to the extension-based guess and then to "text/plain".
        guessed_type, _ = mimetypes.guess_type(safe_filename)
        content_type = (
            file.content_type
            if file.content_type and file.content_type != "application/octet-stream"
            else (guessed_type or "text/plain")
        )
        await storage.upload(
            data=file_content,
            path=storage_path,
            content_type=content_type,
        )
        logger.info(
            "File uploaded to storage",
            path=storage_path,
            user_id=user_id,
        )
    except StorageUploadError as exc:
        logger.error(
            "Storage upload failed, continuing without blob_path",
            filename=file.filename,
            error=str(exc),
        )
        # Non-fatal: ingestion continues without a stored blob.
        # The signed-url endpoint will return 404 if blob_path is None.
        storage_path = None

    # ========================================================================
    # STEP 5: Process document with pipeline
    # ========================================================================

    async def _delete_orphaned_blob(path: str, reason: str) -> None:
        """Best-effort delete of an orphaned storage blob; never raises."""
        try:
            await storage.delete(path)
            logger.info(
                "Orphaned blob deleted",
                path=path,
                reason=reason,
            )
        except (StorageDeleteError, Exception) as del_exc:
            logger.warning(
                "Failed to delete orphaned blob",
                path=path,
                reason=reason,
                error=str(del_exc),
            )

    try:
        # Encode bytes as base64 for JSON-safe transport over Redis broker
        file_bytes_b64 = base64.b64encode(file_content).decode("ascii")

        task = ingest_document_task.delay(
            file_bytes_b64,
            file.filename,
            user_id,
            storage_path,
        )

        logger.info(
            "Ingestion task dispatched",
            task_id=task.id,
            filename=file.filename,
            user_id=user_id,
        )

        # Record the task ID so the status endpoint can distinguish
        # genuinely-queued tasks from unknown/expired IDs (both return
        # PENDING from Celery's AsyncResult).
        try:
            redis = _get_redis()
            await redis.setex(
                f"{_TASK_DISPATCH_KEY_PREFIX}{task.id}",
                _TASK_DISPATCH_TTL,
                "1",
            )
        except Exception as _redis_exc:  # noqa: BLE001
            # Non-fatal — polling will degrade gracefully without the key
            logger.warning(
                "Failed to record task dispatch key in Redis",
                task_id=task.id,
                error=str(_redis_exc),
            )

        return {"task_id": task.id, "status": "processing"}

    except Exception as e:
        logger.error(
            "Failed to dispatch ingestion task",
            filename=file.filename,
            error=str(e),
            user_id=user_id,
            exc_info=True,
        )
        # Clean up orphaned blob — task never ran so storage would leak
        if storage_path:
            await _delete_orphaned_blob(storage_path, "dispatch_error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue ingestion task. Please try again.",
        )


# ============================================================================
# HEALTH CHECK - For testing the endpoint is registered
# ============================================================================


@router.get(
    "/ingest/health",
    status_code=status.HTTP_200_OK,
    summary="Ingestion endpoint health check",
    tags=["health"],
)
async def ingest_health() -> dict[str, str]:
    """
    Health check for ingestion endpoint.

    Returns:
        Status message

    Example:
        ```bash
        curl http://localhost:8000/api/v1/ingest/health
        ```
    """
    return {"status": "ok", "endpoint": "ingest"}


# ============================================================================
# TASK STATUS
# ============================================================================


@router.get(
    "/ingest/status/{task_id}",
    status_code=status.HTTP_200_OK,
    summary="Poll ingestion task status",
    description="Returns the current state of a background ingestion task.",
)
async def get_ingest_status(task_id: str) -> dict:
    """
    Poll the status of a background ingestion task dispatched by POST /ingest.

    States returned:
    - ``processing``  — task is queued or running
    - ``success``     — pipeline completed; ``result`` contains document info
    - ``failure``     — pipeline failed; ``error`` contains the message

    Args:
        task_id: Celery task ID returned by POST /ingest.

    Returns:
        dict with ``task_id``, ``status``, and optionally ``result`` or ``error``.
    """
    result = AsyncResult(task_id, app=celery_app)

    state = result.state  # PENDING | STARTED | SUCCESS | FAILURE | RETRY

    if state in ("PENDING", "STARTED", "RETRY"):
        # PENDING is also returned for unknown/expired task IDs.
        # Consult Redis to confirm this ID was actually dispatched.
        if state == "PENDING":
            try:
                redis = _get_redis()
                exists = await redis.exists(f"{_TASK_DISPATCH_KEY_PREFIX}{task_id}")
            except Exception as _redis_exc:  # noqa: BLE001
                # Redis unavailable — fail open and report as processing
                logger.warning(
                    "Redis unavailable during task existence check; assuming processing",
                    task_id=task_id,
                    error=str(_redis_exc),
                )
                exists = True

            if not exists:
                logger.warning(
                    "Task ID not found in dispatch registry — unknown or expired",
                    task_id=task_id,
                )
                return {
                    "task_id": task_id,
                    "status": "failure",
                    "error": "Task not found or has expired. Please re-upload the document.",
                }

        return {"task_id": task_id, "status": "processing"}

    if state == "SUCCESS":
        return {"task_id": task_id, "status": "success", "result": result.result}

    # FAILURE or unknown
    error_msg = str(result.result) if result.result else "Ingestion failed"
    logger.warning(
        "Ingestion task failed",
        task_id=task_id,
        error=error_msg,
    )
    return {"task_id": task_id, "status": "failure", "error": error_msg}
