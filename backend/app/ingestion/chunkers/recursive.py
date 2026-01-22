"""
Recursive text chunker for Integration Forge.

This module implements recursive character-based text splitting using LangChain.
The recursive strategy tries multiple separators in order, from largest to smallest,
ensuring chunks respect size constraints while preserving natural boundaries.

Design Philosophy:
- Natural Boundaries: Prefer splitting at paragraphs, then sentences, then words
- Context Preservation: Use overlap to maintain continuity between chunks
- Size Constraints: Respect token/character limits for embeddings
- Graceful Degradation: Fall back to character splitting if needed
- Metadata Rich: Track which separator was used for each chunk

Learning Note:
Why Recursive Splitting?
1. **Natural Language Structure**: Text has hierarchy (paragraphs > sentences > words)
2. **Context Quality**: Splitting at natural boundaries preserves meaning
3. **Better Retrieval**: Chunks that are semantically coherent retrieve better
4. **Token Efficiency**: Avoid splitting mid-sentence or mid-word

Example Flow:
Text: "Paragraph 1.\n\nParagraph 2 is very long...\n\nParagraph 3."
1. Try "\n\n" → Creates 3 chunks
2. If Paragraph 2 > chunk_size, split it by "\n" (lines)
3. If still too large, split by ". " (sentences)
4. Last resort: split by " " (words) or character

Compare to simple splitting:
- Simple: "Paragraph 1.\n\nPara" | "graph 2 is very" | "long...\n\nParagrap"
- Recursive: "Paragraph 1." | "Paragraph 2 is very long..." | "Paragraph 3."
"""

from typing import Any, Callable

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.ingestion.chunkers.base import BaseChunker, Chunk, ChunkStrategy
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# DEFAULT SEPARATORS
# ============================================================================

# Learning Note:
# Why this specific order?
# 1. "\n\n" - Paragraph breaks (strongest semantic boundary)
# 2. "\n" - Line breaks (next strongest)
# 3. ". " - Sentence boundaries (preserve complete thoughts)
# 4. " " - Word boundaries (avoid mid-word splits)
# 5. "" - Character level (last resort)

DEFAULT_SEPARATORS = [
    "\n\n",  # Double newline (paragraphs)
    "\n",    # Single newline (lines)
    ". ",    # Period + space (sentences)
    " ",     # Space (words)
    "",      # Character (last resort)
]


# ============================================================================
# RECURSIVE CHUNKER
# ============================================================================


class RecursiveChunker(BaseChunker):
    """
    Recursive character text splitter.

    Uses LangChain's RecursiveCharacterTextSplitter to intelligently split
    text by trying multiple separators in order. Preserves natural language
    boundaries while respecting size constraints.

    Attributes:
        chunk_size: Target size for each chunk (in characters)
        chunk_overlap: Overlap between consecutive chunks
        separators: List of separators to try, in order
        length_function: Function to measure text length
        metadata_prefix: Prefix to add to chunk metadata

    Learning Note:
    When to use RecursiveChunker?
    ✅ General text documents (articles, documentation, guides)
    ✅ Mixed content (prose + code snippets)
    ✅ When you want natural language boundaries
    ❌ Pure code (use CodeAwareChunker instead)
    ❌ When semantic similarity matters more (use SemanticChunker)
    ❌ When you need parent-child hierarchy (use ParentChildChunker)
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: list[str] | None = None,
        length_function: Callable[[str], int] | None = None,
        metadata_prefix: str = "",
    ) -> None:
        """
        Initialize recursive chunker.

        Args:
            chunk_size: Target chunk size in characters (default: 1000)
            chunk_overlap: Overlap between chunks (default: 200)
            separators: Custom separators to try (default: DEFAULT_SEPARATORS)
            length_function: Custom length function (default: len)
            metadata_prefix: Prefix for metadata (e.g., "[Doc: Guide]")

        Learning Note:
        Why allow custom separators?
        - Flexibility: Different document types need different separators
        - Example: Code might use "\n\n\n" for function boundaries
        - Example: Markdown might prioritize "## " for headers
        - Domain-Specific: API docs might split on "### Endpoint"
        """
        super().__init__(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            metadata_prefix=metadata_prefix,
        )

        self.separators = separators or DEFAULT_SEPARATORS
        self.length_function = length_function or len

        # Create LangChain splitter
        # Learning Note:
        # Why delegate to LangChain?
        # - Battle-Tested: LangChain's splitter is used by thousands
        # - Edge Cases: Handles Unicode, empty strings, etc.
        # - Optimization: Efficient implementation
        # - Maintenance: We get bug fixes for free
        # - Focus: We focus on our domain logic, not text splitting
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=self.length_function,
            separators=self.separators,
            keep_separator=True,  # Preserve separators in chunks
        )

        logger.debug(
            "RecursiveChunker initialized",
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=self.separators,
        )

    def chunk(
        self,
        text: str,
        document_metadata: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        """
        Split text into chunks using recursive character splitting.

        Process:
        1. Use LangChain's RecursiveCharacterTextSplitter
        2. Convert LangChain chunks to our Chunk objects
        3. Add metadata (separator used, position, etc.)
        4. Enrich with document metadata
        5. Validate chunks
        6. Return

        Args:
            text: Text to chunk
            document_metadata: Document-level metadata to add

        Returns:
            List of Chunk objects with metadata

        Raises:
            ValueError: If text is empty or chunking fails

        Learning Note:
        Why convert LangChain chunks to our Chunk objects?
        - Type Safety: Our Chunk has validation, metadata, etc.
        - Flexibility: We can add custom fields
        - Consistency: All chunkers return the same Chunk type
        - Testing: Easier to mock and test
        """
        if not text.strip():
            logger.error("Empty text provided for chunking")
            raise ValueError("Empty text provided for chunking")

        logger.debug(
            "Starting recursive chunking",
            text_length=len(text),
            approx_tokens=self.count_tokens(text),
        )

        try:
            # Split using LangChain
            langchain_chunks = self._splitter.split_text(text)

            # Convert to our Chunk objects
            chunks: list[Chunk] = []
            for idx, content in enumerate(langchain_chunks):
                chunk = Chunk(
                    content=content,
                    chunk_index=idx,
                    metadata={
                        "chunk_length": len(content),
                        "approx_tokens": self.count_tokens(content),
                        "separator_strategy": "recursive",
                    },
                )
                chunks.append(chunk)

            # Enrich with document metadata
            if document_metadata:
                self.enrich_metadata(chunks, document_metadata)

            # Validate chunks
            self.validate_chunks(chunks)

            # Log statistics
            self.log_chunk_stats(chunks)

            logger.info(
                "Recursive chunking completed",
                chunk_count=len(chunks),
                original_length=len(text),
            )

            return chunks

        except Exception as e:
            logger.error(
                "Recursive chunking failed",
                error=str(e),
                text_length=len(text),
            )
            raise ValueError(f"Failed to chunk text: {e}") from e

    def get_strategy_name(self) -> ChunkStrategy:
        """Return the chunking strategy identifier."""
        return ChunkStrategy.RECURSIVE

    def detect_separator_used(self, chunk: str) -> str:
        """
        Detect which separator was most likely used for a chunk.

        This is a heuristic - LangChain doesn't expose which separator
        was used, so we infer it based on what's in the chunk.

        Args:
            chunk: Chunk text to analyze

        Returns:
            Most likely separator used. When DEFAULT_SEPARATORS includes
            the empty string (""), this will always return a separator
            (at minimum, the empty string).

        Raises:
            ValueError: If no separator matched and separators list doesn't
                       include empty string (defensive behavior)

        Learning Note:
        Why is this useful?
        - Debugging: See which separators are being used
        - Analytics: Measure which separators work best
        - Optimization: Adjust separator list based on usage
        - Validation: Ensure chunks split at expected boundaries

        Limitation:
        This is a heuristic! If chunk contains multiple separators,
        we return the first match. Not 100% accurate but good enough
        for debugging and analytics.

        Note on empty string (""):
        The empty string is always contained in any string, so if it's
        in the separators list, it will always match (character-level split).
        """
        for separator in self.separators:
            # Skip empty string check first, handle it last
            if separator == "":
                continue
            if separator in chunk:
                return separator
        
        # If we didn't find any non-empty separator, check for empty string
        if "" in self.separators:
            return ""
        
        # Defensive: should not happen with DEFAULT_SEPARATORS, but guard anyway
        raise ValueError(
            f"No separator matched chunk (length: {len(chunk)}). "
            f"Separators list: {self.separators}"
        )

    def add_separator_metadata(self, chunks: list[Chunk]) -> list[Chunk]:
        """
        Add metadata about which separator was used for each chunk.

        This is optional but helpful for debugging and optimization.

        Args:
            chunks: List of chunks to enhance

        Returns:
            Chunks with separator metadata added (modifies in-place)

        Raises:
            ValueError: If separator detection fails (should not happen
                       with DEFAULT_SEPARATORS which includes "")

        Learning Note:
        Why track separators?
        - Quality Metrics: Measure how often we split at natural boundaries
        - Optimization: Adjust separator order based on usage
        - Debugging: See if chunks are splitting where expected
        - Analytics: Compare retrieval quality by separator type
        """
        for chunk in chunks:
            separator = self.detect_separator_used(chunk.content)
            # Empty string separator means character-level splitting
            if separator == "":
                chunk.metadata["separator_used"] = "character"
            else:
                chunk.metadata["separator_used"] = repr(separator)

        return chunks


# ============================================================================
# SPECIALIZED RECURSIVE CHUNKERS
# ============================================================================


class MarkdownRecursiveChunker(RecursiveChunker):
    """
    Recursive chunker optimized for Markdown documents.

    Uses Markdown-specific separators:
    - Headers (##, ###)
    - Horizontal rules (---)
    - Code blocks (```)
    - Paragraphs (\n\n)

    Learning Note:
    Why a separate Markdown chunker?
    - Structure: Markdown has clear hierarchical structure
    - Headers: Preserve header hierarchy for context
    - Code Blocks: Keep code blocks together
    - Lists: Keep list items grouped
    - Better Retrieval: Chunks align with document structure
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        metadata_prefix: str = "",
    ) -> None:
        """Initialize Markdown-optimized recursive chunker."""
        markdown_separators = [
            "\n## ",    # H2 headers
            "\n### ",   # H3 headers
            "\n#### ",  # H4 headers
            "\n---\n",  # Horizontal rules
            "```\n",    # Code block boundaries
            "\n\n",     # Paragraphs
            "\n",       # Lines
            ". ",       # Sentences
            " ",        # Words
            "",         # Characters
        ]

        super().__init__(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=markdown_separators,
            metadata_prefix=metadata_prefix,
        )

        logger.debug("MarkdownRecursiveChunker initialized")


class CodeRecursiveChunker(RecursiveChunker):
    """
    Recursive chunker optimized for code.

    Uses code-specific separators:
    - Function boundaries
    - Class boundaries
    - Block boundaries

    Learning Note:
    For production code chunking, prefer CodeAwareChunker!
    This is a simpler version that just uses different separators.
    CodeAwareChunker uses AST parsing for language-specific handling.

    Use this for:
    - Mixed content (documentation with code snippets)
    - Quick prototyping
    - Languages not supported by CodeAwareChunker
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        metadata_prefix: str = "",
    ) -> None:
        """Initialize code-optimized recursive chunker."""
        code_separators = [
            "\n\n\n",   # Multiple blank lines (function/class boundaries)
            "\n\n",     # Double newline
            "\n",       # Single newline
            " ",        # Space
            "",         # Character
        ]

        super().__init__(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=code_separators,
            metadata_prefix=metadata_prefix,
        )

        logger.debug("CodeRecursiveChunker initialized")
