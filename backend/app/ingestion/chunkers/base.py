"""
Base chunker for Integration Forge.

This module defines the abstract interface for all chunking strategies.
Provides common utilities and data structures for text chunking.

Design Philosophy:
- Strategy Pattern: Multiple chunking algorithms with same interface
- Metadata-Rich: Preserve document context during chunking
- Composability: Easy to chain and combine chunkers
- Type-Safe: Strong typing with dataclasses and protocols
- Extensibility: Easy to add new chunking strategies

Learning Note:
Why use an abstract base class?
1. Contract: All chunkers must implement the same interface
2. Type Safety: Type checkers can verify implementations
3. Code Reuse: Common utilities shared across chunkers
4. Flexibility: Easy to swap chunking strategies
5. Testing: Mock chunkers for unit tests
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# ENUMS - Chunk types and strategies
# ============================================================================


class ChunkType(str, Enum):
    """
    Type of chunk in parent-child indexing.

    Learning Note:
    Parent-Child Strategy:
    - PARENT: Large context chunks (1024+ tokens), NOT embedded
    - CHILD: Small searchable chunks (256 tokens), embedded
    - Search finds children (precise), return parents (contextual)
    """

    PARENT = "parent"
    CHILD = "child"


class ChunkStrategy(str, Enum):
    """
    Chunking strategy identifier.

    Tracks which chunker created each chunk for debugging and analytics.
    """

    RECURSIVE = "recursive"
    SEMANTIC = "semantic"
    PARENT_CHILD = "parent_child"
    CONTEXTUAL = "contextual"
    CODE_AWARE = "code_aware"


# ============================================================================
# DATA STRUCTURES - Chunk representation
# ============================================================================


@dataclass
class Chunk:
    """
    Represents a single text chunk with metadata.

    This is the core data structure passed between chunkers, embedders,
    and the database. Rich metadata enables better retrieval and context.

    Attributes:
        content: The actual text content of the chunk
        chunk_index: Position in the document (0-based)
        metadata: Flexible dict for contextual information
        chunk_type: PARENT or CHILD for parent-child indexing
        parent_chunk_index: Index of parent chunk (if this is a child)

    Metadata Examples:
    {
        "header": "Authentication",
        "page": 5,
        "language": "typescript",
        "chunk_strategy": "recursive",
        "parent_header_chain": ["Docs", "API", "Auth"],
        "semantic_density": 0.85,
        "context_prefix": "[Doc: LangGraph | Section: Agents]"
    }

    Learning Note:
    Why so much metadata?
    - Context: LLM needs to know where chunk came from
    - Debugging: Track which chunker/strategy created it
    - Filtering: Search only code chunks, or only from specific sections
    - Analytics: Measure which sections get queried most
    """

    content: str
    chunk_index: int
    metadata: dict[str, Any] = field(default_factory=dict)
    chunk_type: ChunkType = ChunkType.PARENT
    parent_chunk_index: int | None = None

    def __post_init__(self) -> None:
        """Validate chunk after initialization."""
        if not self.content.strip():
            raise ValueError("Chunk content cannot be empty")
        if self.chunk_index < 0:
            raise ValueError("Chunk index must be non-negative")

    def __len__(self) -> int:
        """Return length of chunk content."""
        return len(self.content)

    def __repr__(self) -> str:
        """String representation for debugging."""
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return (
            f"Chunk(index={self.chunk_index}, "
            f"type={self.chunk_type.value}, "
            f"length={len(self.content)}, "
            f"preview='{preview}')"
        )


# ============================================================================
# BASE CHUNKER - Abstract interface
# ============================================================================


class BaseChunker(ABC):
    """
    Abstract base class for all chunking strategies.

    All chunkers must implement:
    - chunk(): Split text into chunks
    - get_strategy_name(): Return strategy identifier

    Provides common utilities:
    - Token counting
    - Metadata enrichment
    - Logging

    Learning Note:
    Strategy Pattern in Action:
    - RecursiveChunker: Split by separators recursively
    - SemanticChunker: Split by semantic similarity
    - ParentChildChunker: Create hierarchical chunks
    - CodeAwareChunker: Respect code structure
    All implement the same interface, interchangeable!

    Attributes:
        chunk_size: Target size for each chunk (in characters or tokens)
        chunk_overlap: Overlap between consecutive chunks
        metadata_prefix: Prefix to add to all chunk metadata
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        metadata_prefix: str = "",
    ) -> None:
        """
        Initialize base chunker.

        Args:
            chunk_size: Target chunk size (characters or tokens)
            chunk_overlap: Overlap between chunks (for context preservation)
            metadata_prefix: Prefix for metadata (e.g., "[Doc: Guide]")

        Learning Note:
        Why chunk_overlap?
        - Context: Prevents splitting related content
        - Example: "...end of sentence. Start of..." vs "...of sentence."
        - Typical: 10-20% overlap (200 chars for 1000 char chunks)
        - Trade-off: More overlap = more chunks = higher cost
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap cannot be negative")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.metadata_prefix = metadata_prefix

        logger.debug(
            "Chunker initialized",
            strategy=self.get_strategy_name(),
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    @abstractmethod
    def chunk(self, text: str, **kwargs: Any) -> list[Chunk]:
        """
        Split text into chunks.

        This is the main method that each chunking strategy must implement.

        Args:
            text: Text to chunk
            **kwargs: Strategy-specific parameters

        Returns:
            List of Chunk objects with metadata

        Raises:
            NotImplementedError: Must be implemented by subclass

        Learning Note:
        Why abstract method?
        - Forces subclasses to implement
        - Type checker verifies implementation
        - Documents the interface clearly
        """
        pass

    async def achunk(self, text: str, **kwargs: Any) -> list[Chunk]:
        """
        Async version of chunk().

        Default implementation delegates to chunk(), so all existing chunkers
        automatically support async callers (e.g., IngestionPipeline._chunk_text)
        without any changes.

        ContextualChunker overrides this to run concurrent LLM calls for
        per-chunk context enrichment.

        Args:
            text: Text to chunk
            **kwargs: Strategy-specific parameters (forwarded to chunk())

        Returns:
            List of Chunk objects with metadata
        """
        return self.chunk(text, **kwargs)

    @abstractmethod
    def get_strategy_name(self) -> ChunkStrategy:
        """
        Return the chunking strategy identifier.

        Returns:
            ChunkStrategy enum value

        Learning Note:
        Why separate method instead of class variable?
        - Flexibility: Strategy might be dynamic
        - Type Safety: Returns enum, not string
        - Debugging: Can be overridden for testing
        """
        pass

    def enrich_metadata(
        self,
        chunks: list[Chunk],
        document_metadata: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        """
        Enrich chunks with additional metadata.

        Adds:
        - Chunk strategy name
        - Document-level metadata
        - Context prefix (if configured)

        Args:
            chunks: List of chunks to enrich
            document_metadata: Document-level metadata to add

        Returns:
            Chunks with enriched metadata (modifies in-place and returns)

        Learning Note:
        Why enrich after chunking?
        - Separation: Chunking logic separate from metadata
        - Flexibility: Same chunks, different metadata
        - Composability: Can add multiple enrichment passes
        """
        strategy_name = self.get_strategy_name()
        document_metadata = document_metadata or {}

        for chunk in chunks:
            # Add strategy name
            chunk.metadata["chunk_strategy"] = strategy_name.value

            # Add document metadata
            for key, value in document_metadata.items():
                if key not in chunk.metadata:
                    chunk.metadata[key] = value

            # Add context prefix
            if self.metadata_prefix:
                chunk.metadata["context_prefix"] = self.metadata_prefix

        logger.debug(
            "Metadata enriched",
            chunk_count=len(chunks),
            strategy=strategy_name.value,
        )

        return chunks

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text (approximate).

        Uses a simple heuristic: ~4 characters per token.
        For accurate counting, use tiktoken library.

        Args:
            text: Text to count tokens for

        Returns:
            Approximate token count

        Learning Note:
        Why approximate?
        - Performance: tiktoken is slow for real-time chunking
        - Good Enough: 4 chars/token is accurate within 10%
        - Use Case: For limits, approximation is fine
        - Exact Count: Use tiktoken for billing/analytics

        Real token count with tiktoken:
        ```python
        import tiktoken
        encoding = tiktoken.get_encoding("cl100k_base")
        tokens = encoding.encode(text)
        return len(tokens)
        ```
        """
        # Simple heuristic: ~4 characters per token
        # This is accurate within ~10% for English text
        return len(text) // 4

    def validate_chunks(self, chunks: list[Chunk]) -> None:
        """
        Validate generated chunks.

        Checks:
        - All chunks have content
        - Chunk indices are sequential
        - No duplicate indices

        Args:
            chunks: List of chunks to validate

        Raises:
            ValueError: If validation fails

        Learning Note:
        Why validate?
        - Early Detection: Catch chunker bugs immediately
        - Data Quality: Ensure clean data in database
        - Debugging: Clear error messages
        - Testing: Verify chunker correctness
        """
        if not chunks:
            logger.warning("No chunks generated")
            return

        # Check for empty chunks
        for chunk in chunks:
            if not chunk.content.strip():
                raise ValueError(f"Empty chunk at index {chunk.chunk_index}")

        # Check for sequential indices
        indices = [chunk.chunk_index for chunk in chunks]
        expected_indices = list(range(len(chunks)))
        if indices != expected_indices:
            raise ValueError(f"Chunk indices are not sequential: {indices} != {expected_indices}")

        logger.debug(
            "Chunks validated",
            chunk_count=len(chunks),
        )

    def log_chunk_stats(self, chunks: list[Chunk]) -> None:
        """
        Log statistics about generated chunks.

        Useful for debugging and optimization.

        Args:
            chunks: List of chunks to analyze
        """
        if not chunks:
            logger.warning("No chunks to analyze")
            return

        total_length = sum(len(chunk.content) for chunk in chunks)
        avg_length = total_length / len(chunks) if chunks else 0
        min_length = min(len(chunk.content) for chunk in chunks)
        max_length = max(len(chunk.content) for chunk in chunks)

        logger.info(
            "Chunk statistics",
            strategy=self.get_strategy_name().value,
            chunk_count=len(chunks),
            total_chars=total_length,
            avg_chars=int(avg_length),
            min_chars=min_length,
            max_chars=max_length,
            approx_tokens=total_length // 4,  # Use same heuristic as count_tokens
        )


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def combine_chunks(chunks: list[Chunk], separator: str = "\n\n") -> str:
    """
    Combine chunks back into a single text.

    Useful for:
    - Validation: Verify chunking is reversible
    - Testing: Compare original vs reconstructed
    - Debugging: See what was chunked

    Args:
        chunks: List of chunks to combine
        separator: String to join chunks with

    Returns:
        Combined text

    Learning Note:
    Why is this useful?
    - Validation: len(original) ≈ len(combined) (accounting for overlap)
    - Testing: original.split() should ≈ combine(chunk(original))
    - Debugging: See if chunks make sense together
    """
    return separator.join(chunk.content for chunk in chunks)


def get_chunk_by_index(chunks: list[Chunk], index: int) -> Chunk | None:
    """
    Get chunk by its index.

    Args:
        chunks: List of chunks
        index: Chunk index to find

    Returns:
        Chunk with matching index or None
    """
    for chunk in chunks:
        if chunk.chunk_index == index:
            return chunk
    return None
