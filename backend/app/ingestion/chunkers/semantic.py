"""
Semantic chunker using embedding-based boundary detection.

Splits text where the cosine distance between adjacent sentence embeddings
exceeds a configurable threshold — producing topically coherent chunks.

Cost note:
- One embedding call per sentence at ingest time
- Use only when retrieval quality justifies the higher ingest cost

Implemented with langchain_experimental.text_splitter.SemanticChunker.
"""

from typing import Any, Literal

from langchain_experimental.text_splitter import SemanticChunker as LCSemanticChunker
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings
from app.ingestion.chunkers.base import BaseChunker, Chunk, ChunkStrategy
from app.ingestion.embeddings import EmbeddingClient
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SemanticChunker(BaseChunker):
    """
    Embedding-based semantic text chunker.

    Unlike RecursiveChunker which splits on character separators,
    SemanticChunker embeds every sentence and splits where the cosine
    distance between adjacent embeddings exceeds a threshold. This
    produces chunks that are topically coherent rather than merely
    size-bounded.

    Uses the same OpenAI model/dimensions as the app's EmbeddingClient,
    so no extra credentials are required.

    When to use:
    ✅ Long documents where topic shifts mid-page
    ✅ When retrieval precision matters more than ingest cost
    ❌ Short documents (< 500 chars) — sentence-level overhead not worth it
    ❌ High-throughput ingestion on a tight embedding budget
    """

    def __init__(
        self,
        embedding_client: EmbeddingClient,
        buffer_size: int = 1,
        breakpoint_threshold_type: Literal[
            "percentile", "standard_deviation", "interquartile", "gradient"
        ] = "percentile",
        breakpoint_threshold_amount: float | None = None,
        min_chunk_size: int | None = None,
        metadata_prefix: str = "",
    ) -> None:
        """
        Initialize semantic chunker.

        Args:
            embedding_client: App's EmbeddingClient — used to pull the model name
                and dimensions so this chunker uses the exact same embedding
                config as the rest of the system. No new credentials needed.
            buffer_size: Surrounding sentences included in each embedding window.
                buffer_size=1 means (prev, curr, next) are concatenated before
                embedding, giving each breakpoint more local context.
            breakpoint_threshold_type: How to choose the split threshold:
                - "percentile": Split at a percentile of all pairwise distances
                  (default 95th). Good general-purpose choice.
                - "standard_deviation": Split at mean + N * std. Adapts to
                  the overall coherence of the document.
                - "interquartile": Uses IQR upper fence; robust to outliers.
                - "gradient": Detects cliff edges in sorted distances. Best
                  for documents with very sharp topic transitions.
            breakpoint_threshold_amount: Override the default threshold value
                for the chosen type (e.g., 85.0 for 85th percentile).
            min_chunk_size: Minimum character length per chunk. Short chunks
                below this are merged into their neighbour.
            metadata_prefix: Optional prefix stored in metadata['context_prefix'].
        """
        # BaseChunker validation requires chunk_size > 0 and chunk_overlap < chunk_size.
        # Semantic splitting is boundary-driven, not size-driven; pass minimal valid values.
        super().__init__(chunk_size=1, chunk_overlap=0, metadata_prefix=metadata_prefix)

        self._embedding_client = embedding_client
        self._breakpoint_threshold_type = breakpoint_threshold_type

        # Build a LangChain Embeddings bridge that uses the same model and dimensions
        # as our EmbeddingClient. Same OpenAI API key from settings — no new secrets.
        lc_embeddings = OpenAIEmbeddings(
            model=embedding_client.model,
            dimensions=embedding_client.dimensions,
            api_key=settings.openai_api_key,
        )

        splitter_kwargs: dict[str, Any] = {
            "embeddings": lc_embeddings,
            "buffer_size": buffer_size,
            "breakpoint_threshold_type": breakpoint_threshold_type,
            "add_start_index": False,
        }
        if breakpoint_threshold_amount is not None:
            splitter_kwargs["breakpoint_threshold_amount"] = breakpoint_threshold_amount
        if min_chunk_size is not None:
            splitter_kwargs["min_chunk_size"] = min_chunk_size

        self._splitter = LCSemanticChunker(**splitter_kwargs)

        logger.debug(
            "SemanticChunker initialized",
            model=embedding_client.model,
            dimensions=embedding_client.dimensions,
            buffer_size=buffer_size,
            breakpoint_threshold_type=breakpoint_threshold_type,
        )

    def chunk(
        self,
        text: str,
        document_metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> list[Chunk]:
        """
        Split text into semantically coherent chunks.

        Splits where the cosine distance between adjacent sentence embeddings
        exceeds the configured breakpoint threshold.

        Args:
            text: Full document text to split.
            document_metadata: Document-level metadata to attach to each chunk.

        Returns:
            List of Chunk objects. Each chunk includes chunk_strategy='semantic'
            and breakpoint_threshold_type in its metadata.

        Raises:
            ValueError: If text is empty or splitting fails.
        """
        if not text.strip():
            raise ValueError("Empty text provided for chunking")

        logger.debug(
            "Starting semantic chunking",
            text_length=len(text),
            threshold_type=self._breakpoint_threshold_type,
        )

        try:
            raw_chunks = self._splitter.split_text(text)

            chunks: list[Chunk] = []
            for idx, content in enumerate(raw_chunks):
                chunk = Chunk(
                    content=content,
                    chunk_index=idx,
                    metadata={
                        "chunk_strategy": ChunkStrategy.SEMANTIC.value,
                        "chunk_length": len(content),
                        "approx_tokens": self.count_tokens(content),
                        "breakpoint_threshold_type": self._breakpoint_threshold_type,
                    },
                )
                chunks.append(chunk)

            self.enrich_metadata(chunks, document_metadata)
            self.validate_chunks(chunks)
            self.log_chunk_stats(chunks)

            logger.info(
                "Semantic chunking completed",
                chunk_count=len(chunks),
                original_length=len(text),
            )

            return chunks

        except Exception as e:
            logger.error(
                "Semantic chunking failed",
                error=str(e),
                text_length=len(text),
            )
            raise ValueError(f"Failed to chunk text semantically: {e}") from e

    def get_strategy_name(self) -> ChunkStrategy:
        """Return the chunking strategy identifier."""
        return ChunkStrategy.SEMANTIC

