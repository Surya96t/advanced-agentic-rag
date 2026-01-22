"""
Document repository for Integration Forge.

This module handles all database operations for documents with RLS enforcement.
Provides a clean interface for CRUD operations on the documents table.

Design Philosophy:
- RLS First: All queries automatically filtered by user_id via Supabase RLS
- Type Safety: Return Pydantic models, not raw dicts
- Error Handling: Raise custom exceptions for better API error responses
- Async: All methods are async for FastAPI compatibility
- Logging: Structured logs for debugging and observability

Learning Note:
Why use repository pattern?
1. Separation of Concerns: Business logic separate from data access
2. Testability: Easy to mock database operations in tests
3. Consistency: Single source of truth for database queries
4. Type Safety: Strong typing with Pydantic models
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from supabase import Client

from app.database.models import Document, DocumentStatus
from app.utils.errors import DatabaseError, NotFoundError, ConflictError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DocumentRepository:
    """
    Repository for document database operations.

    Handles all CRUD operations for documents with automatic RLS enforcement.

    Learning Note:
    RLS (Row-Level Security) means:
    - All queries are automatically filtered by the authenticated user_id
    - We don't need to add WHERE user_id = xxx to every query
    - Supabase handles this transparently using JWT tokens
    - If a document doesn't belong to the user, it won't be returned

    Attributes:
        db: Supabase client instance
        table_name: Name of the documents table
    """

    def __init__(self, db: Client) -> None:
        """
        Initialize repository with database client.

        Args:
            db: Supabase client instance
        """
        self.db = db
        self.table_name = "documents"

    def create(self, document: Document) -> Document:
        """
        Create a new document record.

        Workflow:
        1. Accept a Document model with all fields populated
        2. Insert into database
        3. Return created document with timestamps

        Args:
            document: Document model to create

        Returns:
            Document: Created document model with timestamps

        Raises:
            DatabaseError: If creation fails

        Learning Note:
        Why accept Document model instead of individual params?
        - Cleaner API: Single parameter
        - Type Safety: Pydantic validates all fields
        - Flexibility: Easy to add new fields
        - Pipeline-friendly: Pipeline creates Document, we just store it

        Note: Duplicate checking is done by the pipeline before calling create
        """
        try:
            now = datetime.utcnow()

            # Prepare document data for insertion
            document_data = {
                "id": str(document.id),
                "user_id": str(document.user_id),
                "title": document.title,
                "file_type": document.file_type,
                "file_size": document.file_size,
                "content_hash": document.content_hash,
                "chunk_count": document.chunk_count,
                "status": document.status.value if isinstance(document.status, DocumentStatus) else document.status,
                "metadata": document.metadata,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }

            # Add optional fields if present
            if document.source_id:
                document_data["source_id"] = str(document.source_id)
            if document.blob_path:
                document_data["blob_path"] = document.blob_path

            logger.info(
                "Creating document",
                document_id=str(document.id),
                user_id=str(document.user_id),
                title=document.title,
            )

            # Insert into database
            result = self.db.table(self.table_name).insert(
                document_data).execute()

            if not result.data or len(result.data) == 0:
                raise DatabaseError(
                    message="Failed to create document",
                    details={"reason": "No data returned from insert"},
                )

            logger.info(
                "Document created successfully",
                document_id=str(document.id),
            )

            # Convert to Pydantic model
            return Document(**result.data[0])

        except Exception as e:
            logger.error(
                "Failed to create document",
                error=str(e),
                document_id=str(document.id),
                exc_info=True,
            )
            raise DatabaseError(
                message="Failed to create document",
                details={"error": str(e)},
            )

    def get_by_id(self, document_id: UUID, user_id: str) -> Document | None:
        """
        Get document by ID.

        RLS Note:
        Even though we pass user_id explicitly, RLS will enforce it.
        This means if the document exists but belongs to another user,
        the query will return empty (as if the document doesn't exist).

        Args:
            document_id: Document UUID
            user_id: User ID for logging (RLS enforces ownership)

        Returns:
            Document model or None if not found

        Raises:
            DatabaseError: If query fails
        """
        try:
            logger.debug(
                "Fetching document by ID",
                document_id=str(document_id),
                user_id=user_id,
            )

            result = (
                self.db.table(self.table_name)
                .select("*")
                .eq("id", str(document_id))
                .execute()
            )

            if not result.data or len(result.data) == 0:
                logger.debug(
                    "Document not found",
                    document_id=str(document_id),
                    user_id=user_id,
                )
                return None

            logger.debug(
                "Document found",
                document_id=str(document_id),
            )

            return Document(**result.data[0])

        except Exception as e:
            logger.error(
                "Failed to get document by ID",
                error=str(e),
                document_id=str(document_id),
                user_id=user_id,
                exc_info=True,
            )
            raise DatabaseError(
                message="Failed to retrieve document",
                details={"error": str(e)},
            )

    def get_by_hash(self, file_hash: str, user_id: str) -> Document | None:
        """
        Get document by content hash (for deduplication).

        Use Case:
        Before uploading a file, check if the user has already uploaded
        the same file (by comparing SHA256 hashes).

        Args:
            file_hash: SHA256 hash of file content
            user_id: User ID for logging (RLS enforces ownership)

        Returns:
            Document model or None if not found

        Raises:
            DatabaseError: If query fails
        """
        try:
            logger.debug(
                "Checking for duplicate document",
                hash=file_hash,
                user_id=user_id,
            )

            result = (
                self.db.table(self.table_name)
                .select("*")
                .eq("content_hash", file_hash)
                .execute()
            )

            if not result.data or len(result.data) == 0:
                logger.debug("No duplicate document found")
                return None

            logger.debug(
                "Duplicate document found",
                document_id=str(result.data[0]["id"]),
            )

            return Document(**result.data[0])

        except Exception as e:
            logger.error(
                "Failed to check for duplicate document",
                error=str(e),
                hash=file_hash,
                user_id=user_id,
                exc_info=True,
            )
            raise DatabaseError(
                message="Failed to check for duplicate",
                details={"error": str(e)},
            )

    def list(
        self,
        user_id: str,
        source_id: UUID | None = None,
        status: DocumentStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Document], int]:
        """
        List documents with filtering and pagination.

        Query Builder:
        - Starts with base query (all documents)
        - Adds filters conditionally (source_id, status)
        - Applies pagination (offset/limit)
        - RLS automatically filters by user_id

        Args:
            user_id: User ID for logging (RLS enforces ownership)
            source_id: Filter by parent source (optional)
            status: Filter by processing status (optional)
            page: Page number (1-indexed)
            page_size: Items per page

        Returns:
            Tuple of (documents list, total count)

        Raises:
            DatabaseError: If query fails

        Learning Note:
        Why return total count separately?
        - Frontend needs it for pagination UI (e.g., "Page 1 of 5")
        - Supabase doesn't return count by default
        - We need two queries: one for data, one for count
        """
        try:
            logger.debug(
                "Listing documents",
                user_id=user_id,
                source_id=str(source_id) if source_id else None,
                status=status.value if status else None,
                page=page,
                page_size=page_size,
            )

            # Build query
            query = self.db.table(self.table_name).select("*")

            # Apply filters
            if source_id:
                query = query.eq("source_id", str(source_id))
            if status:
                query = query.eq("status", status.value)

            # Get total count (before pagination)
            count_result = query.execute()
            total_count = len(count_result.data) if count_result.data else 0

            # Apply pagination
            offset = (page - 1) * page_size
            query = query.range(offset, offset + page_size - 1)

            # Order by created_at descending (newest first)
            query = query.order("created_at", desc=True)

            # Execute query
            result = query.execute()

            documents = [Document(**doc)
                         for doc in result.data] if result.data else []

            logger.debug(
                "Documents retrieved",
                count=len(documents),
                total=total_count,
            )

            return documents, total_count

        except Exception as e:
            logger.error(
                "Failed to list documents",
                error=str(e),
                user_id=user_id,
                exc_info=True,
            )
            raise DatabaseError(
                message="Failed to retrieve documents",
                details={"error": str(e)},
            )

    def update(
        self,
        document_id: UUID,
        updates: dict[str, Any],
    ) -> Document:
        """
        Update document fields.

        Allows updating most fields except immutable ones (id, user_id, content_hash).
        Commonly updated fields:
        - status: Processing state (by pipeline)
        - chunk_count: Number of chunks created
        - metadata: Tags, categories, etc.
        - title: Document name

        Args:
            document_id: Document UUID
            updates: Dictionary of fields to update

        Returns:
            Updated document model

        Raises:
            NotFoundError: If document not found or unauthorized
            DatabaseError: If update fails

        Learning Note:
        Why accept dict instead of individual params?
        - Flexibility: Easy to update any combination of fields
        - Pipeline-friendly: Pipeline can pass status + chunk_count together
        - Extensible: Add new fields without changing signature
        """
        try:
            logger.info(
                "Updating document",
                document_id=str(document_id),
                fields=list(updates.keys()),
            )

            # Add updated_at timestamp
            update_data = {
                **updates,
                "updated_at": datetime.utcnow().isoformat(),
            }

            # Prevent updating immutable fields
            immutable_fields = {"id", "user_id", "content_hash", "created_at"}
            for field in immutable_fields:
                if field in update_data:
                    logger.warning(
                        f"Attempted to update immutable field: {field}",
                        document_id=str(document_id),
                    )
                    del update_data[field]

            # Check if there's anything to update
            if len(update_data) == 1:  # Only updated_at
                logger.warning(
                    "No fields to update",
                    document_id=str(document_id),
                )
                # Just fetch and return current document
                result = (
                    self.db.table(self.table_name)
                    .select("*")
                    .eq("id", str(document_id))
                    .execute()
                )
                if not result.data or len(result.data) == 0:
                    raise NotFoundError(
                        message="Document not found",
                        details={"document_id": str(document_id)},
                    )
                return Document(**result.data[0])

            # Execute update
            result = (
                self.db.table(self.table_name)
                .update(update_data)
                .eq("id", str(document_id))
                .execute()
            )

            if not result.data or len(result.data) == 0:
                raise NotFoundError(
                    message="Document not found or you don't have permission to update it",
                    details={"document_id": str(document_id)},
                )

            logger.info(
                "Document updated successfully",
                document_id=str(document_id),
            )

            return Document(**result.data[0])

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(
                "Failed to update document",
                error=str(e),
                document_id=str(document_id),
                exc_info=True,
            )
            raise DatabaseError(
                message="Failed to update document",
                details={"error": str(e)},
            )

    def update_status(
        self,
        document_id: UUID,
        status: DocumentStatus,
        token_count: int | None = None,
    ) -> Document:
        """
        Update document processing status.

        This method is used by the ingestion pipeline to update:
        - status: PENDING → PROCESSING → COMPLETED/FAILED
        - token_count: Total tokens after processing

        Args:
            document_id: Document UUID
            status: New processing status
            token_count: Total tokens (optional, set when status=COMPLETED)

        Returns:
            Updated document model

        Raises:
            NotFoundError: If document not found
            DatabaseError: If update fails

        Learning Note:
        Why separate method for status updates?
        - Security: Only pipeline should update status, not users
        - Validation: Ensure status transitions are valid
        - Logging: Track status changes for observability
        """
        try:
            logger.info(
                "Updating document status",
                document_id=str(document_id),
                status=status.value,
                token_count=token_count,
            )

            update_data = {
                "status": status.value,
                "updated_at": datetime.utcnow().isoformat(),
            }

            if token_count is not None:
                update_data["token_count"] = token_count

            result = (
                self.db.table(self.table_name)
                .update(update_data)
                .eq("id", str(document_id))
                .execute()
            )

            if not result.data or len(result.data) == 0:
                raise NotFoundError(
                    message="Document not found",
                    details={"document_id": str(document_id)},
                )

            logger.info(
                "Document status updated successfully",
                document_id=str(document_id),
                status=status.value,
            )

            return Document(**result.data[0])

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(
                "Failed to update document status",
                error=str(e),
                document_id=str(document_id),
                exc_info=True,
            )
            raise DatabaseError(
                message="Failed to update document status",
                details={"error": str(e)},
            )

    def delete(self, document_id: UUID, user_id: str) -> bool:
        """
        Delete a document.

        Cascade Behavior (handled by database triggers):
        1. Delete document record
        2. Automatically delete all associated chunks (ON DELETE CASCADE)
        3. Vector embeddings removed with chunks

        Note: This does NOT delete the file from Supabase Storage.
        That should be handled separately by the calling code.

        Args:
            document_id: Document UUID
            user_id: User ID for logging (RLS enforces ownership)

        Returns:
            True if deleted, False if not found

        Raises:
            DatabaseError: If deletion fails

        Learning Note:
        Why not delete the blob here?
        - Separation of Concerns: Repository handles database, not storage
        - Flexibility: Caller might want to archive instead of delete
        - Error Handling: Storage deletion might fail, don't want to rollback DB
        """
        try:
            logger.info(
                "Deleting document",
                document_id=str(document_id),
                user_id=user_id,
            )

            result = (
                self.db.table(self.table_name)
                .delete()
                .eq("id", str(document_id))
                .execute()
            )

            # Check if any rows were deleted
            deleted = result.data and len(result.data) > 0

            if deleted:
                logger.info(
                    "Document deleted successfully",
                    document_id=str(document_id),
                )
            else:
                logger.warning(
                    "Document not found or already deleted",
                    document_id=str(document_id),
                )

            return deleted

        except Exception as e:
            logger.error(
                "Failed to delete document",
                error=str(e),
                document_id=str(document_id),
                user_id=user_id,
                exc_info=True,
            )
            raise DatabaseError(
                message="Failed to delete document",
                details={"error": str(e)},
            )
