"""
Document API schemas for Integration Forge.

These schemas define the request/response models for document upload and management.
They provide a clean API contract separate from internal database models.

Design Philosophy:
- Request schemas validate user input before it reaches the database
- Response schemas hide internal fields (blob_path, hash, user_id)
- Type-safe models enable auto-generated OpenAPI docs
- Validation happens at the API boundary for better security

Learning Note:
Why separate schemas from database models?
1. API versioning: Change response format without breaking DB
2. Security: Hide sensitive internal fields
3. Validation: Different rules for input vs storage
4. Documentation: Clean API contract for frontend developers
"""

from datetime import datetime
from enum import Enum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, ConfigDict

# Re-export DocumentStatus for API use
from app.database.models import DocumentStatus


# ============================================================================
# CONSTANTS - File upload limits
# ============================================================================

# Allowed file extensions for upload
ALLOWED_EXTENSIONS = {".md", ".pdf", ".txt"}

# Maximum file size in bytes (10MB)
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB

# Default pagination size
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


# ============================================================================
# REQUEST SCHEMAS - Incoming data from clients
# ============================================================================


class DocumentUploadRequest(BaseModel):
    """
    Request schema for uploading a new document.

    Workflow:
    1. User selects a file in the frontend
    2. Frontend sends file + source_id to /api/v1/documents/upload
    3. Backend validates extension, size, and source ownership
    4. File is stored in Supabase Storage
    5. Document record created with status = PENDING
    6. Background job processes the document

    Fields:
    - source_id: Which logical folder to upload to
    - title: Optional custom title (defaults to filename)
    - metadata: Optional tags, categories, etc.

    Note: The actual file is sent as multipart/form-data,
    not included in this schema. FastAPI handles it separately.
    """
    source_id: UUID = Field(
        description="ID of the source (folder) to upload to"
    )
    title: str | None = Field(
        default=None,
        max_length=500,
        description="Optional custom title (defaults to filename if not provided)"
    )
    metadata: dict[str, str] | None = Field(
        default=None,
        description="Optional metadata (tags, categories, etc.)",
        examples=[{"tags": "authentication,api", "category": "reference"}]
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "source_id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "LangGraph Quick Start Guide",
                "metadata": {
                    "tags": "langgraph,tutorial",
                    "category": "getting-started"
                }
            }
        }
    )


class DocumentUpdateRequest(BaseModel):
    """
    Request schema for updating document metadata.

    Use Cases:
    - Rename document
    - Update tags/categories
    - Mark as archived

    Note: Cannot update status or processing-related fields.
    Those are managed by the ingestion pipeline.
    """
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=500,
        description="New title for the document"
    )
    metadata: dict[str, str] | None = Field(
        default=None,
        description="Updated metadata (replaces existing)"
    )

    @field_validator("title")
    @classmethod
    def validate_title_not_empty(cls, v: str | None) -> str | None:
        """Ensure title is not just whitespace."""
        if v is not None and not v.strip():
            raise ValueError("Title cannot be empty or whitespace only")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Updated Guide Title",
                "metadata": {
                    "tags": "langgraph,advanced",
                    "category": "tutorials"
                }
            }
        }
    )


# ============================================================================
# RESPONSE SCHEMAS - Outgoing data to clients
# ============================================================================


class DocumentResponse(BaseModel):
    """
    Response schema for a single document.

    Security Note:
    Internal fields are excluded for safety:
    - blob_path: Prevents direct storage access
    - hash: Not relevant to API users
    - user_id: Implied by authentication context

    Fields:
    - id: Unique identifier
    - source_id: Parent source
    - title: Display name
    - status: Processing status
    - token_count: For cost estimation
    - created_at: When uploaded
    - updated_at: Last modification
    """
    id: UUID = Field(
        description="Unique identifier for this document"
    )
    source_id: UUID = Field(
        description="Parent source this document belongs to"
    )
    title: str = Field(
        description="Document title or filename"
    )
    status: DocumentStatus = Field(
        description="Current processing status (pending, processing, completed, failed)"
    )
    token_count: int = Field(
        description="Total tokens in document (for cost estimation)"
    )
    metadata: dict[str, str] | None = Field(
        default=None,
        description="User-provided metadata (tags, categories, etc.)"
    )
    created_at: datetime = Field(
        description="When the document was uploaded (UTC)"
    )
    updated_at: datetime = Field(
        description="When the document was last updated (UTC)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "660e8400-e29b-41d4-a716-446655440001",
                "source_id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "LangGraph Quick Start",
                "status": "completed",
                "token_count": 2500,
                "metadata": {
                    "tags": "langgraph,tutorial",
                    "category": "getting-started"
                },
                "created_at": "2026-01-19T10:05:00Z",
                "updated_at": "2026-01-19T10:07:00Z"
            }
        }
    )


class DocumentUploadResponse(BaseModel):
    """
    Response schema after successful document upload.

    Returns:
    - document: The created document record
    - upload_url: Presigned URL for file upload (if using client-side upload)
    - message: Success message

    Learning Note:
    We return the document immediately with status=PENDING.
    The frontend can poll the status endpoint to check processing progress.
    """
    document: DocumentResponse = Field(
        description="The created document record"
    )
    message: str = Field(
        default="Document uploaded successfully. Processing will begin shortly.",
        description="Success message"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "document": {
                    "id": "660e8400-e29b-41d4-a716-446655440001",
                    "source_id": "550e8400-e29b-41d4-a716-446655440000",
                    "title": "LangGraph Quick Start",
                    "status": "pending",
                    "token_count": 0,
                    "metadata": {"tags": "langgraph,tutorial"},
                    "created_at": "2026-01-19T10:05:00Z",
                    "updated_at": "2026-01-19T10:05:00Z"
                },
                "message": "Document uploaded successfully. Processing will begin shortly."
            }
        }
    )


class DocumentListResponse(BaseModel):
    """
    Response schema for paginated list of documents.

    Pagination:
    - page: Current page number (1-indexed)
    - page_size: Items per page
    - total: Total number of documents
    - documents: Array of document records

    Learning Note:
    Pagination is essential for performance:
    - Prevents loading thousands of records at once
    - Enables infinite scroll in frontend
    - Reduces API response time
    """
    documents: list[DocumentResponse] = Field(
        description="Array of document records"
    )
    total: int = Field(
        ge=0,
        description="Total number of documents matching the query"
    )
    page: int = Field(
        ge=1,
        description="Current page number (1-indexed)"
    )
    page_size: int = Field(
        ge=1,
        le=MAX_PAGE_SIZE,
        description="Number of items per page"
    )
    has_more: bool = Field(
        description="Whether there are more pages available"
    )

    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        if self.page_size == 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "documents": [
                    {
                        "id": "660e8400-e29b-41d4-a716-446655440001",
                        "source_id": "550e8400-e29b-41d4-a716-446655440000",
                        "title": "LangGraph Quick Start",
                        "status": "completed",
                        "token_count": 2500,
                        "metadata": {"tags": "langgraph,tutorial"},
                        "created_at": "2026-01-19T10:05:00Z",
                        "updated_at": "2026-01-19T10:07:00Z"
                    }
                ],
                "total": 42,
                "page": 1,
                "page_size": 20,
                "has_more": True
            }
        }
    )


class DocumentDeleteResponse(BaseModel):
    """
    Response schema after successful document deletion.

    Cascade Behavior:
    When a document is deleted:
    1. All associated chunks are deleted (CASCADE)
    2. File is deleted from Supabase Storage
    3. Vector embeddings are removed

    Returns:
    - id: ID of the deleted document
    - message: Confirmation message
    """
    id: UUID = Field(
        description="ID of the deleted document"
    )
    message: str = Field(
        default="Document and associated chunks deleted successfully",
        description="Confirmation message"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "660e8400-e29b-41d4-a716-446655440001",
                "message": "Document and associated chunks deleted successfully"
            }
        }
    )


# ============================================================================
# FILTER SCHEMAS - Query parameters for listing documents
# ============================================================================


class DocumentListFilters(BaseModel):
    """
    Query parameters for filtering and paginating documents.

    Use Cases:
    - GET /api/v1/documents?source_id=xxx&status=completed&page=1
    - Filter by status to show only failed uploads
    - Filter by source to show documents in a specific folder

    Fields:
    - source_id: Filter by parent source (optional)
    - status: Filter by processing status (optional)
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20, max: 100)
    """
    source_id: UUID | None = Field(
        default=None,
        description="Filter by parent source ID"
    )
    status: DocumentStatus | None = Field(
        default=None,
        description="Filter by processing status"
    )
    page: int = Field(
        default=1,
        ge=1,
        description="Page number (1-indexed)"
    )
    page_size: int = Field(
        default=DEFAULT_PAGE_SIZE,
        ge=1,
        le=MAX_PAGE_SIZE,
        description="Number of items per page (max 100)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "source_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "completed",
                "page": 1,
                "page_size": 20
            }
        }
    )


# ============================================================================
# HELPER FUNCTIONS - Validation utilities
# ============================================================================


def validate_file_extension(filename: str) -> bool:
    """
    Validate that the uploaded file has an allowed extension.

    Args:
        filename: Name of the uploaded file

    Returns:
        True if extension is allowed, False otherwise

    Learning Note:
    Path traversal prevention: We only check the extension,
    not the full path, to avoid security issues.
    """
    import os
    _, ext = os.path.splitext(filename.lower())
    return ext in ALLOWED_EXTENSIONS


def validate_file_size(file_size_bytes: int) -> bool:
    """
    Validate that the uploaded file is within size limits.

    Args:
        file_size_bytes: Size of the file in bytes

    Returns:
        True if file size is acceptable, False otherwise

    Learning Note:
    10MB limit chosen because:
    1. OpenAI API max context: ~100k tokens (~400k chars)
    2. Average token-to-char ratio: 1 token = 4 chars
    3. 10MB ≈ 10M chars ≈ 2.5M tokens (way over limit)
    4. Chunking brings this down to reasonable size
    5. Large files should be split by user before upload
    """
    return 0 < file_size_bytes <= MAX_FILE_SIZE_BYTES


def get_file_extension_error_message() -> str:
    """
    Get a user-friendly error message for invalid file extensions.

    Returns:
        Error message listing allowed extensions
    """
    allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
    return f"Invalid file type. Allowed extensions: {allowed}"


def get_file_size_error_message() -> str:
    """
    Get a user-friendly error message for oversized files.

    Returns:
        Error message with size limit
    """
    max_mb = MAX_FILE_SIZE_BYTES / (1024 * 1024)
    return f"File too large. Maximum size: {max_mb:.0f}MB"
