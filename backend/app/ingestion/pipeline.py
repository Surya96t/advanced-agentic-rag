"""
Ingestion pipeline for Integration Forge.

This module orchestrates the complete document ingestion workflow:
Parse → Chunk → Embed → Store in Supabase

Design Philosophy:
- Orchestration: Coordinate all ingestion components
- Resilience: Handle errors gracefully with rollback
- Observability: Track progress and emit events
- Efficiency: Batch operations for performance
- Idempotency: Deduplication to avoid re-processing

Learning Note:
Why a pipeline class?
- Single Responsibility: Each component does one thing
- Composability: Easy to swap chunkers, embedders, etc.
- Testability: Mock dependencies in unit tests
- Observability: Central place to track progress
- Error Handling: Coordinate rollback across components

Pipeline Flow:
1. Check for duplicates (content hash)
2. Parse document (extract text)
3. Create document record in DB
4. Chunk text (RecursiveChunker)
5. Generate embeddings (OpenAI API, batched)
6. Store chunks (Supabase, batched)
7. Update document status
8. Return document

Error Handling:
- Parse failure → mark document as failed
- Embedding failure → retry 3x, then fail
- Storage failure → rollback document record
- Partial success → store what we can, mark status
"""

import hashlib
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import UUID

from app.database.client import SupabaseClient
from app.database.models import Document, DocumentChunk, DocumentStatus
from app.database.repositories.chunks import ChunkRepository
from app.database.repositories.documents import DocumentRepository
from app.ingestion.chunkers.base import Chunk
from app.ingestion.chunkers.recursive import RecursiveChunker
from app.ingestion.embeddings import EmbeddingClient, get_embedding_client
from app.ingestion.parser import DocumentParser, ParsedDocument
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# PROGRESS TRACKING
# ============================================================================


class IngestionProgress:
    """
    Track ingestion progress and emit events.

    Used to provide real-time feedback during document processing.
    """

    def __init__(self) -> None:
        """Initialize progress tracker."""
        self.current_stage: str = "idle"
        self.percentage: float = 0.0
        self.message: str = ""
        self.started_at: datetime = datetime.now(timezone.utc)

    def update(
        self,
        stage: str,
        percentage: float,
        message: str = "",
    ) -> None:
        """
        Update progress state.

        Args:
            stage: Current processing stage
            percentage: Completion percentage (0-100)
            message: Optional progress message
        """
        self.current_stage = stage
        self.percentage = percentage
        self.message = message

        logger.info(
            "Ingestion progress",
            stage=stage,
            percentage=f"{percentage:.1f}%",
            message=message,
        )

    def get_state(self) -> dict[str, Any]:
        """
        Get current progress state.

        Returns:
            Dictionary with progress information
        """
        elapsed = (datetime.now(timezone.utc) -
                   self.started_at).total_seconds()

        return {
            "stage": self.current_stage,
            "percentage": self.percentage,
            "message": self.message,
            "elapsed_seconds": round(elapsed, 2),
        }


# ============================================================================
# INGESTION PIPELINE
# ============================================================================


class IngestionPipeline:
    """
    Orchestrate document ingestion: parse → chunk → embed → store.

    This is the main entry point for processing documents in the RAG system.
    Coordinates all ingestion components and handles the complete workflow.

    Attributes:
        doc_repo: Repository for document operations
        chunk_repo: Repository for chunk operations
        parser: Document parser for text extraction
        chunker: Text chunker for splitting documents
        embedding_client: Client for generating embeddings

    Learning Note:
    Why dependency injection?
    - Testing: Easy to mock repositories and clients
    - Flexibility: Swap chunkers, embedders without changing code
    - Configuration: Different settings for different document types
    - Observability: Inject loggers, tracers, etc.
    """

    def __init__(
        self,
        doc_repo: DocumentRepository,
        chunk_repo: ChunkRepository,
        embedding_client: EmbeddingClient,
        chunker: RecursiveChunker | None = None,
        parser: DocumentParser | None = None,
    ) -> None:
        """
        Initialize ingestion pipeline.

        Args:
            doc_repo: Document repository instance
            chunk_repo: Chunk repository instance
            embedding_client: Embedding client instance
            chunker: Text chunker (default: RecursiveChunker)
            parser: Document parser (default: DocumentParser)

        Learning Note:
        Why default to RecursiveChunker?
        - General Purpose: Works well for most document types
        - Natural Boundaries: Respects paragraphs, sentences
        - Proven: Used by LangChain, battle-tested
        - Customizable: Can override for specific needs
        """
        self.doc_repo = doc_repo
        self.chunk_repo = chunk_repo
        self.embedding_client = embedding_client
        self.chunker = chunker or RecursiveChunker(
            chunk_size=1000,
            chunk_overlap=200,
        )
        self.parser = parser or DocumentParser()

        logger.info(
            "IngestionPipeline initialized",
            chunker_type=type(self.chunker).__name__,
        )

    async def ingest_document(
        self,
        file_bytes: bytes,
        filename: str,
        user_id: str,  # Clerk user ID (e.g., "user_2bXYZ123")
        source_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> Document:
        """
        Ingest a document through the complete pipeline.

        This is the main entry point that orchestrates:
        1. Duplicate detection
        2. Document parsing
        3. Text chunking
        4. Embedding generation
        5. Database storage

        Args:
            file_bytes: Raw file content
            filename: Name of the file
            user_id: ID of user uploading document
            source_id: Optional source ID for grouping
            metadata: Optional metadata to attach
            progress_callback: Optional callback for progress updates

        Returns:
            Processed Document object

        Raises:
            ValueError: If file format unsupported or parsing fails
            Exception: If embedding or storage fails

        Learning Note:
        Why return Document, not chunks?
        - Document is the main entity user cares about
        - Chunks are implementation details
        - User can query chunks via document_id later
        - Cleaner API: ingest_document → get Document

        Example:
        ```python
        pipeline = IngestionPipeline(...)
        doc = await pipeline.ingest_document(
            file_bytes=pdf_bytes,
            filename="api_guide.pdf",
            user_id=user.id,
            metadata={"category": "documentation"}
        )
        print(f"Ingested {doc.chunk_count} chunks")
        ```
        """
        progress = IngestionProgress()

        def emit_progress(stage: str, percentage: float, message: str = "") -> None:
            """Helper to emit progress updates."""
            progress.update(stage, percentage, message)
            if progress_callback:
                progress_callback(progress.get_state())

        try:
            emit_progress("starting", 0, f"Processing {filename}")

            # Step 1: Check for duplicates (5%)
            emit_progress("deduplication", 5, "Checking for duplicates")
            content_hash = self._compute_hash(file_bytes)
            existing_doc = await self.doc_repo.get_by_hash(
                file_hash=content_hash,
                user_id=str(user_id),
            )

            if existing_doc:
                logger.info(
                    "Duplicate document detected",
                    filename=filename,
                    existing_doc_id=existing_doc.id,
                )
                emit_progress("complete", 100, "Document already exists")
                return existing_doc

            # Step 2: Parse document (10-20%)
            emit_progress("parsing", 10, "Extracting text from document")
            parsed_doc = await self._parse_document(file_bytes, filename)
            emit_progress(
                "parsing", 20, f"Extracted {len(parsed_doc.content)} characters")

            # Step 3: Create document record (25%)
            emit_progress("creating", 25, "Creating document record")
            document = await self._create_document_record(
                user_id=user_id,
                source_id=source_id,
                filename=filename,
                content_hash=content_hash,
                metadata=metadata or {},
                parsed_doc=parsed_doc,
            )

            # Step 4: Chunk text (30-40%)
            emit_progress("chunking", 30, "Splitting text into chunks")

            # Merge user metadata with parsed metadata for chunks
            full_metadata = {
                **parsed_doc.metadata,
                **(metadata or {}),
            }

            chunks = await self._chunk_text(
                text=parsed_doc.content,
                document_id=document.id,
                document_metadata=full_metadata,
            )
            emit_progress("chunking", 40, f"Created {len(chunks)} chunks")

            # Step 5: Generate embeddings (45-70%)
            emit_progress("embedding", 45, "Generating embeddings")
            embeddings = await self._generate_embeddings(
                chunks=chunks,
                progress_callback=lambda pct: emit_progress(
                    "embedding",
                    45 + (pct * 0.25),  # 45% to 70%
                    f"Embedding chunks ({pct:.0f}% complete)",
                ),
            )
            emit_progress("embedding", 70, "Embeddings generated")

            # Step 6: Store chunks (75-90%)
            emit_progress("storing", 75, "Storing chunks in database")
            await self._store_chunks(
                document_id=document.id,
                user_id=user_id,
                chunks=chunks,
                embeddings=embeddings,
            )
            emit_progress("storing", 90, f"Stored {len(chunks)} chunks")

            # Step 7: Update document status (95%)
            emit_progress("finalizing", 95, "Finalizing document")
            document = await self._finalize_document(
                document_id=document.id,
                chunk_count=len(chunks),
                status=DocumentStatus.COMPLETED,
            )

            # Step 8: Complete (100%)
            emit_progress("complete", 100, "Document ingestion complete")

            logger.info(
                "Document ingestion successful",
                document_id=document.id,
                filename=filename,
                chunks=len(chunks),
                elapsed_seconds=progress.get_state()["elapsed_seconds"],
            )

            return document

        except Exception as e:
            logger.error(
                "Document ingestion failed",
                filename=filename,
                error=str(e),
                error_type=type(e).__name__,
            )
            emit_progress("error", 0, f"Error: {str(e)}")

            # Try to mark document as failed if it was created
            if 'document' in locals():
                try:
                    await self._finalize_document(
                        document_id=document.id,  # type: ignore
                        chunk_count=0,
                        status=DocumentStatus.FAILED,
                        error_message=str(e),
                    )
                except Exception as cleanup_error:
                    logger.error("Failed to mark document as failed",
                                 error=str(cleanup_error))

            raise

    async def _parse_document(
        self,
        file_bytes: bytes,
        filename: str,
    ) -> ParsedDocument:
        """
        Parse document to extract text.

        Args:
            file_bytes: Raw file content
            filename: Name of file (used to detect format)

        Returns:
            ParsedDocument with text and metadata

        Raises:
            ValueError: If parsing fails
        """
        try:
            parsed = self.parser.parse_from_bytes(file_bytes, filename)
            logger.debug(
                "Document parsed",
                filename=filename,
                text_length=len(parsed.content),
                format=parsed.metadata.get("format"),
            )
            return parsed
        except Exception as e:
            logger.error(
                "Document parsing failed",
                filename=filename,
                error=str(e),
            )
            raise ValueError(f"Failed to parse document: {e}") from e

    async def _chunk_text(
        self,
        text: str,
        document_id: UUID,
        document_metadata: dict[str, Any],
    ) -> list[Chunk]:
        """
        Chunk text into smaller pieces.

        Args:
            text: Full document text
            document_id: ID of parent document
            document_metadata: Metadata to add to chunks

        Returns:
            List of Chunk objects

        Raises:
            ValueError: If chunking fails
        """
        try:
            # Add document_id to metadata
            enriched_metadata = {
                **document_metadata,
                "document_id": str(document_id),
            }

            chunks = self.chunker.chunk(
                text=text,
                document_metadata=enriched_metadata,
            )

            logger.debug(
                "Text chunked",
                document_id=document_id,
                chunk_count=len(chunks),
            )

            return chunks
        except Exception as e:
            logger.error(
                "Text chunking failed",
                document_id=document_id,
                error=str(e),
            )
            raise ValueError(f"Failed to chunk text: {e}") from e

    async def _generate_embeddings(
        self,
        chunks: list[Chunk],
        progress_callback: Callable[[float], None] | None = None,
    ) -> list[list[float]]:
        """
        Generate embeddings for chunks.

        Args:
            chunks: List of text chunks
            progress_callback: Optional callback for progress (0-100)

        Returns:
            List of embedding vectors

        Raises:
            Exception: If embedding generation fails

        Learning Note:
        Why batch embeddings?
        - Efficiency: 100 texts in 1 API call vs 100 calls
        - Cost: Same tokens, fewer API overhead charges
        - Rate Limits: Less likely to hit requests/min limit
        - The EmbeddingClient handles batching internally
        """
        try:
            # Extract text from chunks
            texts = [chunk.content for chunk in chunks]

            # Generate embeddings (client handles batching)
            embeddings = await self.embedding_client.embed_texts(
                texts=texts,
                show_progress=True,
            )

            # Report progress if callback provided
            if progress_callback:
                progress_callback(100.0)

            logger.debug(
                "Embeddings generated",
                chunk_count=len(chunks),
                embedding_dimensions=len(embeddings[0]) if embeddings else 0,
            )

            return embeddings
        except Exception as e:
            logger.error(
                "Embedding generation failed",
                chunk_count=len(chunks),
                error=str(e),
            )
            raise

    async def _store_chunks(
        self,
        document_id: UUID,
        user_id: str,  # Clerk user ID
        chunks: list[Chunk],
        embeddings: list[list[float]],
    ) -> None:
        """
        Store chunks in database with embeddings.

        Args:
            document_id: ID of parent document
            user_id: Clerk user ID of the owner
            chunks: List of text chunks
            embeddings: List of embedding vectors

        Raises:
            Exception: If storage fails

        Learning Note:
        Why batch inserts?
        - Performance: 100 rows in 1 query vs 100 queries
        - Database Load: Fewer round-trips to database
        - Transaction Safety: All-or-nothing per batch
        - Supabase has limits on batch size (~1000 rows)
        """
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Chunk count ({len(chunks)}) != embedding count ({len(embeddings)})"
            )

        try:
            # Convert Chunks to dictionaries for create_batch
            # NOTE: create_batch expects list[dict], not list[DocumentChunk]
            chunk_dicts = []
            for chunk, embedding in zip(chunks, embeddings):
                chunk_dict = {
                    "document_id": document_id,
                    "user_id": user_id,  # Already a string (Clerk user ID)
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "embedding": embedding,
                    "metadata": chunk.metadata,
                    "chunk_type": chunk.chunk_type.value,
                    "parent_chunk_id": None,  # Will be set in parent-child indexing
                }
                chunk_dicts.append(chunk_dict)

            # Batch insert (repository handles ID generation and timestamps)
            await self.chunk_repo.create_batch(chunk_dicts)

            logger.debug(
                "Chunks stored",
                document_id=document_id,
                chunk_count=len(chunks),
            )
        except Exception as e:
            logger.error(
                "Chunk storage failed",
                document_id=document_id,
                chunk_count=len(chunks),
                error=str(e),
            )
            raise

    async def _create_document_record(
        self,
        user_id: str,  # Clerk user ID
        source_id: UUID | None,
        filename: str,
        content_hash: str,
        metadata: dict[str, Any],
        parsed_doc: ParsedDocument,
    ) -> Document:
        """
        Create document record in database.

        Args:
            user_id: Clerk user ID of the uploader
            source_id: Optional source ID
            filename: Name of file
            content_hash: Hash of file content
            metadata: User-provided metadata
            parsed_doc: Parsed document with extracted metadata

        Returns:
            Created Document object

        Raises:
            Exception: If database operation fails
        """
        try:
            # Merge metadata from parsing and user input
            full_metadata = {
                **parsed_doc.metadata,
                **metadata,
                "original_filename": filename,
            }

            document = Document(
                user_id=user_id,
                source_id=source_id,
                title=metadata.get("title", filename),
                content_hash=content_hash,
                file_type=parsed_doc.metadata.get("file_type", "unknown"),
                file_size=len(parsed_doc.content),
                metadata=full_metadata,
                status=DocumentStatus.PROCESSING,
                chunk_count=0,
            )

            created_doc = await self.doc_repo.create(document)

            logger.debug(
                "Document record created",
                document_id=created_doc.id,
                filename=filename,
            )

            return created_doc
        except Exception as e:
            logger.error(
                "Document record creation failed",
                filename=filename,
                error=str(e),
            )
            raise

    async def _finalize_document(
        self,
        document_id: UUID,
        chunk_count: int,
        status: DocumentStatus,
        error_message: str | None = None,
    ) -> Document:
        """
        Update document status after processing.

        Args:
            document_id: ID of document to update
            chunk_count: Number of chunks created
            status: Final status (COMPLETED or FAILED)
            error_message: Optional error message if failed

        Returns:
            Updated Document object

        Raises:
            Exception: If update fails
        """
        try:
            updates = {
                "status": status.value,
                "chunk_count": chunk_count,
            }

            if error_message:
                updates["metadata"] = {"error": error_message}

            updated_doc = await self.doc_repo.update(document_id, updates)

            logger.debug(
                "Document finalized",
                document_id=document_id,
                status=status.value,
                chunk_count=chunk_count,
            )

            return updated_doc
        except Exception as e:
            logger.error(
                "Document finalization failed",
                document_id=document_id,
                error=str(e),
            )
            raise

    def _compute_hash(self, content: bytes) -> str:
        """
        Compute SHA-256 hash of content for deduplication.

        Args:
            content: File content bytes

        Returns:
            Hexadecimal hash string

        Learning Note:
        Why SHA-256?
        - Collision Resistant: Virtually impossible to find two files with same hash
        - Fast: Can hash megabytes in milliseconds
        - Standard: Widely used for content addressing
        - Deterministic: Same content = same hash always

        Use Case:
        - Deduplication: Don't re-process same document
        - Change Detection: Re-process if content changes
        - Content Addressing: Use hash as unique identifier
        """
        return hashlib.sha256(content).hexdigest()


# ============================================================================
# FACTORY FUNCTION
# ============================================================================


async def get_ingestion_pipeline() -> IngestionPipeline:
    """
    Factory function to create ingestion pipeline with dependencies.

    Returns:
        Configured IngestionPipeline instance

    Learning Note:
    Why a factory function?
    - Dependency Injection: All dependencies created here
    - Testing: Easy to mock by overriding factory
    - Configuration: Single place to configure pipeline
    - FastAPI Integration: Use with Depends() for auto-injection

    Usage in FastAPI:
    ```python
    @app.post("/ingest")
    async def ingest_document(
        file: UploadFile,
        pipeline: IngestionPipeline = Depends(get_ingestion_pipeline)
    ):
        doc = await pipeline.ingest_document(...)
        return {"document_id": doc.id}
    ```
    """
    supabase = SupabaseClient.get_client()
    doc_repo = DocumentRepository(supabase)
    chunk_repo = ChunkRepository(supabase)
    embedding_client = await get_embedding_client()

    return IngestionPipeline(
        doc_repo=doc_repo,
        chunk_repo=chunk_repo,
        embedding_client=embedding_client,
    )
