"""
Document ingestion API endpoint for Integration Forge.

This endpoint handles document upload and triggers the ingestion pipeline.

Workflow:
1. User uploads a file via POST /api/v1/ingest
2. Validate file type and size
3. Read file content
4. Call IngestionPipeline to process the document
5. Return document record with status

TODO Phase 6: Add Clerk JWT authentication
- Add @require_auth decorator
- Extract user_id from JWT token instead of query parameter
- Add rate limiting per user
- Add user quota validation

Learning Note:
Why separate upload from processing?
1. Quick response: Return immediately with status=PROCESSING
2. Async processing: Heavy work (embedding, chunking) happens in background
3. User feedback: Frontend can poll status endpoint for progress
4. Scalability: Can queue uploads if processing is slow

For now, we process synchronously to keep it simple.
Phase 4 will add background job processing with Celery/Redis.
"""

from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from supabase import Client

from app.database.client import SupabaseClient
from app.database.repositories.chunks import ChunkRepository
from app.database.repositories.documents import DocumentRepository
from app.ingestion.embeddings import get_embedding_client
from app.ingestion.pipeline import IngestionPipeline
from app.schemas.document import (
    DocumentResponse,
    MAX_FILE_SIZE_BYTES,
    get_file_extension_error_message,
    get_file_size_error_message,
    validate_file_extension,
    validate_file_size,
)
from app.utils.errors import ValidationError
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/api/v1", tags=["ingestion"])


# ============================================================================
# DEPENDENCIES
# ============================================================================


def get_db() -> Client:
    """
    Get Supabase database client.

    Returns:
        Supabase client instance

    Learning Note:
    FastAPI dependency injection:
    - This function is called automatically by FastAPI
    - Result is passed to route handlers
    - Enables easy mocking in tests
    """
    return SupabaseClient.get_client()


async def get_pipeline(db: Client = Depends(get_db)) -> IngestionPipeline:
    """
    Get ingestion pipeline with all dependencies.

    Args:
        db: Supabase client (injected by FastAPI)

    Returns:
        Configured IngestionPipeline instance

    Learning Note:
    Why create pipeline in dependency?
    1. Reusability: Same pipeline setup for all endpoints
    2. Testability: Easy to override in tests
    3. Clean code: Route handlers stay focused on HTTP logic
    """
    doc_repo = DocumentRepository(db)
    chunk_repo = ChunkRepository(db)
    embedding_client = await get_embedding_client()

    return IngestionPipeline(
        doc_repo=doc_repo,
        chunk_repo=chunk_repo,
        embedding_client=embedding_client,
    )


# ============================================================================
# ROUTES
# ============================================================================


@router.post(
    "/ingest",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest a document",
    description=(
        "Upload a document file for ingestion. "
        "Supported formats: Markdown (.md), PDF (.pdf), Text (.txt). "
        "Maximum file size: 10MB. "
        "The document will be parsed, chunked, embedded, and stored in the vector database."
    ),
    responses={
        201: {
            "description": "Document successfully ingested",
            "model": DocumentResponse,
        },
        400: {
            "description": "Invalid file type or size",
            "content": {
                "application/json": {
                    "example": {
                        "error": "ValidationError",
                        "message": "Invalid file type. Allowed extensions: .md, .pdf, .txt",
                        "status_code": 400,
                        "details": {},
                    }
                }
            },
        },
        413: {
            "description": "File too large",
            "content": {
                "application/json": {
                    "example": {
                        "error": "ValidationError",
                        "message": "File too large. Maximum size: 10MB",
                        "status_code": 413,
                        "details": {},
                    }
                }
            },
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
    # TODO Phase 6: Remove this parameter, extract from Clerk JWT instead
    user_id: Annotated[
        str,
        Query(
            description=(
                "User ID (Clerk format: user_xxx). "
                "TODO Phase 6: This will be extracted from JWT token automatically."
            ),
            examples=["user_2bXYZ123"],
        ),
    ],
    request: Request,
    pipeline: IngestionPipeline = Depends(get_pipeline),
) -> DocumentResponse:
    """
    Upload and ingest a document.

    This endpoint handles the complete document ingestion workflow:
    1. Validate file type and size
    2. Save file temporarily
    3. Parse document content
    4. Chunk text into semantic segments
    5. Generate embeddings for each chunk
    6. Store chunks in vector database
    7. Return document record

    Args:
        file: Uploaded file (multipart/form-data)
        user_id: User ID in Clerk format (temporary, will be from JWT in Phase 6)
        pipeline: Ingestion pipeline dependency

    Returns:
        DocumentResponse: Created document with metadata

    Raises:
        ValidationError: If file type or size is invalid
        HTTPException: If processing fails

    Example cURL:
        ```bash
        curl -X POST "http://localhost:8000/api/v1/ingest?user_id=user_test123" \\
             -F "file=@/path/to/document.md"
        ```

    Example Response:
        ```json
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "source_id": "660e8400-e29b-41d4-a716-446655440000",
            "title": "document.md",
            "status": "completed",
            "token_count": 2500,
            "metadata": null,
            "created_at": "2026-01-21T10:00:00Z",
            "updated_at": "2026-01-21T10:00:30Z"
        }
        ```

    TODO Phase 6:
    - Add @require_auth decorator
    - Extract user_id from JWT token
    - Remove user_id query parameter
    - Add rate limiting (e.g., 10 uploads per hour per user)
    - Add user quota validation (e.g., max 100MB storage per user)
    """
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
    if hasattr(file, 'size') and file.size is not None:
        file_size = file.size
        logger.debug(
            "File size from file.size attribute",
            filename=file.filename,
            size_bytes=file_size,
        )

    # Method 2: Check Content-Length header
    elif 'content-length' in request.headers:
        try:
            file_size = int(request.headers['content-length'])
            logger.debug(
                "File size from Content-Length header",
                filename=file.filename,
                size_bytes=file_size,
            )
        except (ValueError, TypeError) as e:
            logger.warning(
                "Invalid Content-Length header",
                filename=file.filename,
                error=str(e),
            )

    # Method 3: If size is available, validate before reading
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

            file_content = b''.join(chunks)
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
    # STEP 4: Process document with pipeline
    # ========================================================================

    try:
        document = await pipeline.ingest_document(
            file_bytes=file_content,
            filename=file.filename,
            user_id=user_id,
        )

        logger.info(
            "Document ingestion completed",
            document_id=str(document.id),
            filename=file.filename,
            status=document.status.value,
            chunk_count=document.metadata.get("chunk_count", 0)
            if document.metadata
            else 0,
            user_id=user_id,
        )

        # Convert to response schema
        return DocumentResponse(
            id=document.id,
            source_id=document.source_id or UUID(
                "00000000-0000-0000-0000-000000000000"),  # Default if None
            title=document.title,
            status=document.status,
            token_count=document.chunk_count * 500,  # Rough estimate: 500 tokens per chunk
            metadata=document.metadata,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )

    except Exception as e:
        logger.error(
            "Document ingestion failed",
            filename=file.filename,
            error=str(e),
            user_id=user_id,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document ingestion failed. Please try again or contact support.",
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
