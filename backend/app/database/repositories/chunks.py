"""
Chunk repository for Advanced Agentic RAG.

This module handles all database operations for document chunks with vector search.
Provides batch operations, parent-child navigation, and semantic search capabilities.

Design Philosophy:
- Batch First: Chunks are created in bulk (100+ at a time) for performance
- Vector Search: Native pgvector integration for semantic similarity
- Parent-Child Support: Navigate hierarchical chunk relationships
- RLS Enforcement: All queries automatically filtered by user_id
- Type Safety: Return Pydantic models with proper validation

Learning Note:
Why is this the most complex repository?
1. Vector Operations: Semantic search with embeddings
2. Batch Processing: Handle 100+ chunks per document
3. Parent-Child: Support hierarchical retrieval strategies
4. Performance Critical: This is called millions of times in production
"""

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from supabase import Client

from app.database.models import ChunkType, DocumentChunk
from app.utils.errors import DatabaseError, NotFoundError
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _parse_embedding(embedding_str: str | list[float] | None) -> list[float] | None:
    """
    Parse embedding from Supabase response.

    Supabase returns vector columns as strings like "[-0.035,0.041,...]".
    We need to parse them back to Python lists.

    Args:
        embedding_str: String representation of vector or None

    Returns:
        List of floats or None
    """
    if embedding_str is None:
        return None
    if isinstance(embedding_str, list):
        return embedding_str
    if isinstance(embedding_str, str):
        # Parse string representation: "[-0.035,0.041,...]" -> [-0.035,0.041,...]
        return json.loads(embedding_str)
    return None


class ChunkRepository:
    """
    Repository for document chunk operations.

    Handles CRUD operations, batch processing, and vector search for chunks.

    Learning Note:
    Chunks are the core of RAG:
    - Each document is split into many chunks
    - Each chunk has a vector embedding
    - Vector search finds semantically similar chunks
    - Retrieved chunks provide context to the LLM

    Attributes:
        db: Supabase client instance
        table_name: Name of the document_chunks table
    """

    def __init__(self, db: Client) -> None:
        """
        Initialize repository with database client.

        Args:
            db: Supabase client instance
        """
        self.db = db
        self.table_name = "document_chunks"

    def create_batch(
        self,
        chunks: list[dict[str, Any]],
    ) -> list[DocumentChunk]:
        """
        Create multiple chunks in a batch operation.

        This is the primary method for inserting chunks after document processing.
        Optimized for bulk insertion (100+ chunks at once).

        Expected chunk dict structure:
        {
            "document_id": UUID,
            "user_id": str,
            "chunk_index": int,
            "content": str,
            "metadata": dict,
            "embedding": list[float] | None,
            "parent_chunk_id": UUID | None,
            "chunk_type": "parent" | "child"
        }

        Args:
            chunks: List of chunk dictionaries to insert

        Returns:
            List of created DocumentChunk models

        Raises:
            DatabaseError: If batch insertion fails

        Learning Note:
        Why batch insertion?
        - Performance: 100 chunks in 1 query vs 100 separate queries
        - Atomicity: All chunks inserted together or none
        - Cost: Reduces database connection overhead
        - Typical document: 50-200 chunks, so batching is essential
        """
        if not chunks:
            logger.warning("create_batch called with empty chunks list")
            return []

        try:
            logger.info(
                "Creating chunk batch",
                chunk_count=len(chunks),
                document_id=str(chunks[0].get("document_id")),
            )

            # Prepare chunks with generated IDs and timestamps
            now = datetime.now(UTC)
            prepared_chunks = []

            for chunk in chunks:
                chunk_data = {
                    "id": str(uuid4()),
                    "document_id": str(chunk["document_id"]),
                    "user_id": chunk["user_id"],
                    "chunk_index": chunk["chunk_index"],
                    "content": chunk["content"],
                    "metadata": chunk.get("metadata", {}),
                    "embedding": chunk.get("embedding"),
                    "parent_chunk_id": str(chunk["parent_chunk_id"])
                    if chunk.get("parent_chunk_id")
                    else None,
                    "chunk_type": chunk.get("chunk_type", ChunkType.PARENT.value),
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                }
                prepared_chunks.append(chunk_data)

            # Batch insert
            result = self.db.table(self.table_name).insert(prepared_chunks).execute()

            if not result.data:
                raise DatabaseError(
                    message="Failed to create chunks",
                    details={"reason": "No data returned from insert"},
                )

            logger.info(
                "Chunks created successfully",
                chunk_count=len(result.data),
            )

            # Convert to Pydantic models using prepared data
            # NOTE: Convert string UUIDs back to UUID objects for Pydantic model
            pydantic_chunks = []
            for chunk_data in prepared_chunks:
                # Convert string UUIDs to UUID objects
                model_data = {
                    **chunk_data,
                    "id": UUID(chunk_data["id"]),
                    "document_id": UUID(chunk_data["document_id"]),
                    "parent_chunk_id": UUID(chunk_data["parent_chunk_id"])
                    if chunk_data.get("parent_chunk_id")
                    else None,
                    "created_at": datetime.fromisoformat(chunk_data["created_at"]),
                    "updated_at": datetime.fromisoformat(chunk_data["updated_at"]),
                }
                pydantic_chunks.append(DocumentChunk(**model_data))

            return pydantic_chunks

        except Exception as e:
            logger.error(
                "Failed to create chunk batch",
                error=str(e),
                chunk_count=len(chunks),
                exc_info=True,
            )
            raise DatabaseError(
                message="Failed to create chunks",
                details={"error": str(e)},
            )

    def get_by_id(self, chunk_id: UUID, user_id: str) -> DocumentChunk | None:
        """
        Get chunk by ID.

        Args:
            chunk_id: Chunk UUID
            user_id: User ID for logging (RLS enforces ownership)

        Returns:
            DocumentChunk model or None if not found

        Raises:
            DatabaseError: If query fails
        """
        try:
            logger.debug(
                "Fetching chunk by ID",
                chunk_id=str(chunk_id),
                user_id=user_id,
            )

            result = self.db.table(self.table_name).select("*").eq("id", str(chunk_id)).execute()

            if not result.data or len(result.data) == 0:
                logger.debug(
                    "Chunk not found",
                    chunk_id=str(chunk_id),
                )
                return None

            logger.debug(
                "Chunk found",
                chunk_id=str(chunk_id),
            )

            # Parse embedding from string format
            chunk_data = result.data[0]
            chunk_data["embedding"] = _parse_embedding(chunk_data.get("embedding"))

            return DocumentChunk(**chunk_data)

        except Exception as e:
            logger.error(
                "Failed to get chunk by ID",
                error=str(e),
                chunk_id=str(chunk_id),
                exc_info=True,
            )
            raise DatabaseError(
                message="Failed to retrieve chunk",
                details={"error": str(e)},
            )

    def get_by_document_id(
        self,
        document_id: UUID,
        user_id: str,
        chunk_type: ChunkType | None = None,
    ) -> list[DocumentChunk]:
        """
        Get all chunks for a specific document.

        Args:
            document_id: Document UUID
            user_id: User ID for logging (RLS enforces ownership)
            chunk_type: Filter by chunk type (parent/child), optional

        Returns:
            List of DocumentChunk models ordered by chunk_index

        Raises:
            DatabaseError: If query fails

        Learning Note:
        Why order by chunk_index?
        - Chunks must be in document order for context
        - Index 0 is the first chunk, index N is the last
        - Important for reconstructing document or showing previews
        """
        try:
            logger.debug(
                "Fetching chunks by document ID",
                document_id=str(document_id),
                chunk_type=chunk_type.value if chunk_type else None,
                user_id=user_id,
            )

            query = self.db.table(self.table_name).select("*").eq("document_id", str(document_id))

            if chunk_type:
                query = query.eq("chunk_type", chunk_type.value)

            # Order by chunk_index to maintain document order
            query = query.order("chunk_index", desc=False)

            result = query.execute()

            # Parse chunks and convert string embeddings to lists
            chunks = []
            if result.data:
                for chunk_data in result.data:
                    # Parse embedding from string format
                    chunk_data["embedding"] = _parse_embedding(chunk_data.get("embedding"))
                    chunks.append(DocumentChunk(**chunk_data))

            logger.debug(
                "Chunks retrieved",
                document_id=str(document_id),
                count=len(chunks),
            )

            return chunks

        except Exception as e:
            logger.error(
                "Failed to get chunks by document ID",
                error=str(e),
                document_id=str(document_id),
                exc_info=True,
            )
            raise DatabaseError(
                message="Failed to retrieve chunks",
                details={"error": str(e)},
            )

    def get_parent_chunk(
        self,
        child_chunk_id: UUID,
        user_id: str,
    ) -> DocumentChunk | None:
        """
        Get the parent chunk for a given child chunk.

        Used in parent-child retrieval strategy:
        1. Search finds child chunks (small, specific)
        2. Retrieve parent chunks (large, contextual)
        3. Return parent chunks to LLM for better context

        Args:
            child_chunk_id: Child chunk UUID
            user_id: User ID for logging (RLS enforces ownership)

        Returns:
            Parent DocumentChunk or None if not found

        Raises:
            DatabaseError: If query fails

        Learning Note:
        Parent-Child Strategy:
        - Child chunks: Small (256 tokens), highly specific, embedded
        - Parent chunks: Large (1024 tokens), rich context, NOT embedded
        - Search on children → Return parents for context
        - Best of both worlds: precision + context
        """
        try:
            # First, get the child chunk to find parent_chunk_id
            child = self.get_by_id(child_chunk_id, user_id)
            if not child or not child.parent_chunk_id:
                logger.debug(
                    "Child chunk has no parent",
                    child_chunk_id=str(child_chunk_id),
                )
                return None

            # Now get the parent chunk
            return self.get_by_id(child.parent_chunk_id, user_id)

        except DatabaseError:
            # Re-raise existing DatabaseError without wrapping
            raise
        except Exception as e:
            logger.error(
                "Failed to get parent chunk",
                error=str(e),
                child_chunk_id=str(child_chunk_id),
                exc_info=True,
            )
            raise DatabaseError(
                message="Failed to retrieve parent chunk",
                details={"error": str(e)},
            )

    def get_children_chunks(
        self,
        parent_chunk_id: UUID,
        user_id: str,
    ) -> list[DocumentChunk]:
        """
        Get all child chunks for a given parent chunk.

        Args:
            parent_chunk_id: Parent chunk UUID
            user_id: User ID for logging (RLS enforces ownership)

        Returns:
            List of child DocumentChunk models

        Raises:
            DatabaseError: If query fails
        """
        try:
            logger.debug(
                "Fetching children chunks",
                parent_chunk_id=str(parent_chunk_id),
                user_id=user_id,
            )

            result = (
                self.db.table(self.table_name)
                .select("*")
                .eq("parent_chunk_id", str(parent_chunk_id))
                .order("chunk_index", desc=False)
                .execute()
            )

            # Parse chunks and convert string embeddings to lists
            chunks = []
            if result.data:
                for chunk_data in result.data:
                    # Parse embedding from string format
                    chunk_data["embedding"] = _parse_embedding(chunk_data.get("embedding"))
                    chunks.append(DocumentChunk(**chunk_data))

            logger.debug(
                "Children chunks retrieved",
                parent_chunk_id=str(parent_chunk_id),
                count=len(chunks),
            )

            return chunks

        except Exception as e:
            logger.error(
                "Failed to get children chunks",
                error=str(e),
                parent_chunk_id=str(parent_chunk_id),
                exc_info=True,
            )
            raise DatabaseError(
                message="Failed to retrieve children chunks",
                details={"error": str(e)},
            )

    def vector_search(
        self,
        query_embedding: list[float],
        user_id: str,
        limit: int = 10,
        document_id: UUID | None = None,
    ) -> list[tuple[DocumentChunk, float]]:
        """
        Perform semantic similarity search using vector embeddings.

        Uses pgvector's cosine distance operator (<->) for fast similarity search.
        The HNSW index (created in migration) makes this O(log n) instead of O(n).

        Args:
            query_embedding: Query vector (1536 dimensions for text-embedding-3-small)
            user_id: User ID (RLS enforces ownership)
            limit: Maximum number of results to return
            document_id: Filter by specific document (optional)

        Returns:
            List of tuples (chunk, similarity_score)
            - similarity_score: 0.0 (identical) to 2.0 (opposite)
            - Lower score = more similar

        Raises:
            DatabaseError: If search fails

        Learning Note:
        Vector Search Mechanics:
        1. Query embedding generated from user question
        2. pgvector computes cosine distance to all chunk embeddings
        3. HNSW index accelerates nearest neighbor search
        4. RLS filters results to only user's chunks
        5. Returns top-k most similar chunks

        Cosine Distance vs Similarity:
        - Distance = 1 - cosine_similarity
        - Distance 0.0 = identical vectors
        - Distance 2.0 = opposite vectors
        - Lower is better (more similar)
        """
        try:
            logger.debug(
                "Performing vector search",
                user_id=user_id,
                limit=limit,
                document_id=str(document_id) if document_id else None,
            )

            # Build RPC call for vector search
            # Note: Supabase Python client doesn't have direct vector operators yet,
            # so we'll use a custom RPC function defined in the migration.
            # For now, we'll use a workaround with select and manual filtering.

            # This is a simplified version. In production, you'd create a stored procedure
            # or use PostgREST's vector search capabilities directly.
            query = self.db.table(self.table_name).select("*")

            if document_id:
                query = query.eq("document_id", str(document_id))

            # Only search chunks that have embeddings
            query = query.not_.is_("embedding", "null")

            result = query.execute()

            if not result.data:
                logger.debug("No chunks with embeddings found")
                return []

            # Manual similarity calculation (inefficient, but works for demo)
            # In production, use stored procedure with pgvector operators
            import numpy as np

            chunks_with_scores = []
            for chunk_data in result.data:
                # Parse embedding from string format
                chunk_data["embedding"] = _parse_embedding(chunk_data.get("embedding"))
                chunk = DocumentChunk(**chunk_data)
                if chunk.embedding:
                    # Cosine distance calculation
                    query_vec = np.array(query_embedding)
                    chunk_vec = np.array(chunk.embedding)

                    # Normalize vectors
                    query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-10)
                    chunk_norm = chunk_vec / (np.linalg.norm(chunk_vec) + 1e-10)

                    # Cosine similarity
                    cosine_sim = np.dot(query_norm, chunk_norm)

                    # Convert to distance (0 = identical, 2 = opposite)
                    distance = 1 - cosine_sim

                    chunks_with_scores.append((chunk, float(distance)))

            # Sort by distance (ascending = most similar first)
            chunks_with_scores.sort(key=lambda x: x[1])

            # Return top-k results
            results = chunks_with_scores[:limit]

            logger.debug(
                "Vector search completed",
                results_count=len(results),
                top_score=results[0][1] if results else None,
            )

            return results

        except Exception as e:
            logger.error(
                "Failed to perform vector search",
                error=str(e),
                user_id=user_id,
                exc_info=True,
            )
            raise DatabaseError(
                message="Failed to perform vector search",
                details={"error": str(e)},
            )

    def update_embedding(
        self,
        chunk_id: UUID,
        embedding: list[float],
    ) -> DocumentChunk:
        """
        Update chunk embedding.

        Used when regenerating embeddings with a different model or version.

        Args:
            chunk_id: Chunk UUID
            embedding: New embedding vector (1536 dimensions)

        Returns:
            Updated DocumentChunk model

        Raises:
            NotFoundError: If chunk not found
            DatabaseError: If update fails
        """
        try:
            logger.info(
                "Updating chunk embedding",
                chunk_id=str(chunk_id),
            )

            update_data = {
                "embedding": embedding,
                "updated_at": datetime.now(UTC).isoformat(),
            }

            result = (
                self.db.table(self.table_name).update(update_data).eq("id", str(chunk_id)).execute()
            )

            if not result.data or len(result.data) == 0:
                raise NotFoundError(
                    message="Chunk not found",
                    details={"chunk_id": str(chunk_id)},
                )

            logger.info(
                "Chunk embedding updated successfully",
                chunk_id=str(chunk_id),
            )

            # Parse embedding from string format
            chunk_data = result.data[0]
            chunk_data["embedding"] = _parse_embedding(chunk_data.get("embedding"))

            return DocumentChunk(**chunk_data)

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(
                "Failed to update chunk embedding",
                error=str(e),
                chunk_id=str(chunk_id),
                exc_info=True,
            )
            raise DatabaseError(
                message="Failed to update chunk embedding",
                details={"error": str(e)},
            )

    def delete_by_document_id(
        self,
        document_id: UUID,
        user_id: str,
    ) -> int:
        """
        Delete all chunks for a specific document.

        Used when:
        - Reprocessing a document (delete old chunks, create new)
        - Document is deleted (handled by CASCADE, but can be called explicitly)

        Args:
            document_id: Document UUID
            user_id: User ID for logging (RLS enforces ownership)

        Returns:
            Number of chunks deleted

        Raises:
            DatabaseError: If deletion fails

        Learning Note:
        Why bulk delete?
        - Reprocessing: User uploads new version or changes chunking strategy
        - Cleanup: Remove all traces of a document
        - Performance: Delete 100+ chunks in one query
        """
        try:
            logger.info(
                "Deleting chunks by document ID",
                document_id=str(document_id),
                user_id=user_id,
            )

            result = (
                self.db.table(self.table_name)
                .delete()
                .eq("document_id", str(document_id))
                .execute()
            )

            deleted_count = len(result.data) if result.data else 0

            logger.info(
                "Chunks deleted successfully",
                document_id=str(document_id),
                deleted_count=deleted_count,
            )

            return deleted_count

        except Exception as e:
            logger.error(
                "Failed to delete chunks by document ID",
                error=str(e),
                document_id=str(document_id),
                user_id=user_id,
                exc_info=True,
            )
            raise DatabaseError(
                message="Failed to delete chunks",
                details={"error": str(e)},
            )
