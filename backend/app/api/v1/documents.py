"""
Document management API endpoints.

This module provides CRUD operations for managing documents in the system.

Phase 5: Uses hardcoded user_id for testing without authentication
Phase 6: Will add JWT authentication and enforce RLS policies
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import UserID
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


# ============================================================================
# Endpoints
# ============================================================================


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List all documents",
    description="Get a list of all documents for the current user",
)
def list_documents(user_id: UserID) -> DocumentListResponse:
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
        document = doc_repo.get(document_id)
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
