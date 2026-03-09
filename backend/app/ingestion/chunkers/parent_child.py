"""
Parent-child chunking strategy.

Creates two tiers of chunks per document:

- **Parent** (~1024 tokens)  — large context window, stored WITHOUT embedding (NULL).
  Returned to the LLM for rich, coherent answers.
- **Child**  (~256 tokens)   — small, focused, stored WITH embedding.
  Used by vector search to pinpoint the most relevant passage.

Retrieval flow
--------------
1. Vector / hybrid search scores and ranks *child* chunks.
2. ``HybridSearcher._swap_children_for_parents()`` replaces each child's
   content with its parent's content before passing results to the LLM.
3. Citations still use child metadata (document_title, score) for transparency.

Why this is better than a single tier
--------------------------------------
* Embedding dense, short children → sharper semantic precision.
* Returning large parents → LLM sees full surrounding context.
* Zero extra API cost: parents are never embedded.
"""

from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.ingestion.chunkers.base import BaseChunker, Chunk, ChunkStrategy, ChunkType
from app.utils.logger import get_logger

logger = get_logger(__name__)

_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


class ParentChildChunker(BaseChunker):
    """
    Hierarchical chunker that produces parent + child chunks.

    Args:
        parent_chunk_size:    Target character size for parent chunks (default 1024).
        parent_chunk_overlap: Overlap between consecutive parents (default 200).
        child_chunk_size:     Target character size for child chunks (default 256).
        child_chunk_overlap:  Overlap between consecutive children (default 32).
    """

    def __init__(
        self,
        parent_chunk_size: int = 1024,
        parent_chunk_overlap: int = 200,
        child_chunk_size: int = 256,
        child_chunk_overlap: int = 32,
    ) -> None:
        # Store parent parameters in the BaseChunker fields for consistency.
        # chunk_overlap < chunk_size is enforced by BaseChunker.__init__.
        super().__init__(
            chunk_size=parent_chunk_size,
            chunk_overlap=parent_chunk_overlap,
        )
        self.child_chunk_size = child_chunk_size
        self.child_chunk_overlap = child_chunk_overlap

        self._parent_splitter = RecursiveCharacterTextSplitter(
            chunk_size=parent_chunk_size,
            chunk_overlap=parent_chunk_overlap,
            separators=_SEPARATORS,
        )
        self._child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=child_chunk_size,
            chunk_overlap=child_chunk_overlap,
            separators=_SEPARATORS,
        )

        logger.debug(
            "ParentChildChunker initialised",
            parent_chunk_size=parent_chunk_size,
            child_chunk_size=child_chunk_size,
        )

    # ------------------------------------------------------------------
    # BaseChunker interface
    # ------------------------------------------------------------------

    def chunk(self, text: str, **kwargs: Any) -> list[Chunk]:
        """
        Split *text* into a flat list of parent and child chunks.

        Layout of the returned list
        ---------------------------
        Index [0 … P-1]          — P parent ``Chunk`` objects in document order.
        Index [P … P+C-1]        — C child ``Chunk`` objects.  Each child's
                                   ``parent_chunk_index`` points to the parent's
                                   ``chunk_index``.

        Parent chunks carry ``chunk_type=PARENT``.  The ingestion pipeline
        stores them with ``embedding=NULL``; the retrieval layer later fetches
        them by their DB UUID.

        Child chunks carry ``chunk_type=CHILD`` and are fully embedded.

        Args:
            text:                    Full document text.
            **kwargs:                May include ``document_metadata: dict``.

        Returns:
            Flat list of :class:`~app.ingestion.chunkers.base.Chunk` objects,
            parents followed by children.

        Raises:
            ValueError: If *text* is empty.
        """
        if not text.strip():
            raise ValueError("Cannot chunk empty text")

        document_metadata: dict[str, Any] = kwargs.get("document_metadata", {})

        # ----------------------------------------------------------------
        # Step 1: parent chunks
        # ----------------------------------------------------------------
        parent_texts = self._parent_splitter.split_text(text)
        parent_chunks: list[Chunk] = []

        for parent_idx, parent_text in enumerate(parent_texts):
            parent_chunks.append(
                Chunk(
                    content=parent_text,
                    chunk_index=parent_idx,
                    chunk_type=ChunkType.PARENT,
                    parent_chunk_index=None,
                    metadata={
                        **document_metadata,
                        "chunk_strategy": ChunkStrategy.PARENT_CHILD.value,
                        "chunk_type": ChunkType.PARENT.value,
                    },
                )
            )

        # ----------------------------------------------------------------
        # Step 2: child chunks — derived from each parent's text
        # ----------------------------------------------------------------
        child_chunks: list[Chunk] = []
        global_child_idx = len(parent_chunks)  # children start after all parents

        for parent_chunk in parent_chunks:
            child_texts = self._child_splitter.split_text(parent_chunk.content)

            for child_text in child_texts:
                child_chunks.append(
                    Chunk(
                        content=child_text,
                        chunk_index=global_child_idx,
                        chunk_type=ChunkType.CHILD,
                        parent_chunk_index=parent_chunk.chunk_index,
                        metadata={
                            **document_metadata,
                            "chunk_strategy": ChunkStrategy.PARENT_CHILD.value,
                            "chunk_type": ChunkType.CHILD.value,
                            "parent_chunk_index": parent_chunk.chunk_index,
                        },
                    )
                )
                global_child_idx += 1

        logger.debug(
            "ParentChildChunker produced chunks",
            parent_count=len(parent_chunks),
            child_count=len(child_chunks),
        )

        # Parents first so pipeline can insert them and resolve IDs before children.
        return parent_chunks + child_chunks

    def get_strategy_name(self) -> ChunkStrategy:
        return ChunkStrategy.PARENT_CHILD

