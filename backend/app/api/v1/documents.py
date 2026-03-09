"""
Document management API endpoints.

This module provides CRUD operations for managing documents in the system.

Phase 5: Uses hardcoded user_id for testing without authentication
Phase 6: Will add JWT authentication and enforce RLS policies
"""

import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from app.api.deps import UserID, RateLimitInfo
from app.core.storage import StorageClient, StorageNotFoundError, StorageSignedUrlError, get_storage_client
from app.database.client import get_db
from app.database.repositories.documents import DocumentRepository
from app.database.models import Document
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


# Response schemas
class DocumentListItem(BaseModel):
    """Single document in list response."""

    id: UUID
    title: str
    source_id: UUID | None
    status: str
    chunk_count: int | None = Field(
        default=None, description="Number of chunks (if available)")
    created_at: str

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Response schema for document list endpoint."""

    documents: list[DocumentListItem]
    total: int


class DocumentDeleteResponse(BaseModel):
    """Response schema for document delete endpoint."""

    deleted: bool
    document_id: UUID
    chunks_deleted: int


class SignedUrlResponse(BaseModel):
    """Response schema for the signed-URL endpoint."""

    url: str = Field(description="Time-limited HTTPS URL granting read access to the original file")
    expires_in: int = Field(3600, description="URL validity in seconds")


# ============================================================================
# Endpoints
# ============================================================================


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List all documents",
    description="Get a list of all documents for the current user",
)
def list_documents(
    user_id: UserID,
    rate_limit_info: RateLimitInfo,
    response: Response,
) -> DocumentListResponse:
    """
    List all documents for the current user.

    Phase 5: Uses hardcoded user_id from dependency
    Phase 6: Will use JWT-authenticated user_id

    Args:
        user_id: Current user ID (injected via dependency)

    Returns:
        List of documents with metadata

    Raises:
        HTTPException: 500 if database error occurs
    """
    limit, remaining, reset_time = rate_limit_info
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(reset_time)

    logger.info("Listing documents", extra={"user_id": user_id})

    try:
        # Get Supabase client and repository
        supabase = get_db()
        doc_repo = DocumentRepository(supabase)

        # Fetch documents for user
        documents, total_count = doc_repo.list(user_id=user_id)

        # Convert to response schema
        document_items = [
            DocumentListItem(
                id=doc.id,
                title=doc.title,
                source_id=doc.source_id,
                status=doc.status,
                chunk_count=doc.chunk_count,
                created_at=doc.created_at.isoformat() if doc.created_at else "",
            )
            for doc in documents
        ]

        logger.info(
            "Documents listed successfully",
            extra={"user_id": user_id, "count": len(document_items)}
        )

        return DocumentListResponse(
            documents=document_items,
            total=total_count
        )

    except Exception as e:
        logger.error(
            "Failed to list documents",
            extra={"user_id": user_id, "error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve documents: {str(e)}"
        )


@router.delete(
    "/{document_id}",
    response_model=DocumentDeleteResponse,
    summary="Delete a document",
    description="Delete a document and all its associated chunks",
)
def delete_document(
    document_id: UUID,
    user_id: UserID
) -> DocumentDeleteResponse:
    """
    Delete a document and all its chunks.

    This endpoint:
    1. Verifies the document exists
    2. Checks user ownership (RLS simulation)
    3. Deletes all associated chunks
    4. Deletes the document

    Phase 5: Simulates RLS by checking user_id match
    Phase 6: Will enforce RLS at database layer with JWT

    Args:
        document_id: UUID of document to delete
        user_id: Current user ID (injected via dependency)

    Returns:
        Deletion confirmation with counts

    Raises:
        HTTPException: 404 if document not found
        HTTPException: 403 if user doesn't own document
        HTTPException: 500 if database error occurs
    """
    logger.info(
        "Deleting document",
        extra={"user_id": user_id, "document_id": str(document_id)}
    )

    try:
        # Get Supabase client and repositories
        supabase = get_db()
        doc_repo = DocumentRepository(supabase)

        # Verify document exists and get it
        document = doc_repo.get_by_id(document_id, user_id)
        if not document:
            logger.warning(
                "Document not found",
                extra={"document_id": str(document_id), "user_id": user_id}
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found"
            )

        # Check ownership (RLS simulation for Phase 5)
        if document.user_id != user_id:
            logger.warning(
                "Unauthorized document deletion attempt",
                extra={
                    "document_id": str(document_id),
                    "user_id": user_id,
                    "owner_id": document.user_id
                }
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this document"
            )

        # Atomic deletion using PostgreSQL RPC (see migration 005)
        # - Wraps both chunk and document deletion in a single transaction
        # - Automatic rollback if either operation fails
        # - No orphaned chunks or partial deletions possible
        # - RLS policies enforced at database layer
        result = doc_repo.delete_with_chunks(document_id, user_id)

        logger.info(
            "Document deleted successfully (atomic)",
            extra={
                "document_id": str(document_id),
                "user_id": user_id,
                "chunks_deleted": result.get("chunks_deleted", 0),
                "title": result.get("title", "unknown")
            }
        )

        return DocumentDeleteResponse(
            deleted=True,
            document_id=document_id,
            chunks_deleted=result.get("chunks_deleted", 0)
        )

    except HTTPException:
        # Re-raise HTTP exceptions (404, 403)
        raise

    except Exception as e:
        logger.error(
            "Failed to delete document",
            extra={
                "document_id": str(document_id),
                "user_id": user_id,
                "error": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}"
        )


# ============================================================================
# GET /{document_id}/signed-url
# ============================================================================


def _get_storage() -> StorageClient:
    return get_storage_client()


@router.get(
    "/{document_id}/signed-url",
    response_model=SignedUrlResponse,
    summary="Get a signed URL for a document's original file",
    description=(
        "Generate a time-limited pre-signed URL that grants read access "
        "to the original uploaded file stored in Supabase Storage. "
        "Only the document owner may request a URL."
    ),
)
async def get_document_signed_url(
    document_id: UUID,
    user_id: UserID,
    storage: StorageClient = Depends(_get_storage),
) -> SignedUrlResponse:
    """
    Return a 1-hour signed URL for the original file of *document_id*.

    Args:
        document_id: UUID of the document.
        user_id:     Authenticated user (injected via dependency).
        storage:     StorageClient (injected via dependency).

    Returns:
        SignedUrlResponse with ``url`` and ``expires_in``.

    Raises:
        HTTPException 404: Document not found or not owned by caller.
        HTTPException 404: Document has no stored file (blob_path is None).
        HTTPException 500: Signed URL generation failed.
    """
    supabase = await asyncio.to_thread(get_db)
    doc_repo = DocumentRepository(supabase)

    document = await asyncio.to_thread(doc_repo.get_by_id, document_id, user_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    if document.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this document",
        )

    if not document.blob_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No stored file found for this document",
        )

    try:
        expires_in = 3600
        url = await storage.get_signed_url(path=document.blob_path, expires_in=expires_in)
        logger.info(
            "Signed URL generated",
            extra={"document_id": str(document_id), "user_id": user_id},
        )
        return SignedUrlResponse(url=url, expires_in=expires_in)
    except StorageNotFoundError as exc:
        logger.warning(
            "Stored file not found when generating signed URL",
            extra={"document_id": str(document_id), "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stored file not found for this document",
        ) from exc
    except StorageSignedUrlError as exc:
        logger.warning(
            "Failed to generate signed URL",
            extra={"document_id": str(document_id), "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate a download URL for this document",
        ) from exc
