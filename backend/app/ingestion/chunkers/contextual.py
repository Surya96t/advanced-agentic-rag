"""
Contextual enrichment chunker — Anthropic 2024 contextual retrieval pattern.

A decorator that wraps any BaseChunker and enriches each chunk with a
1-2 sentence LLM-generated context prefix that situates the chunk within
the full document. The enriched content is what gets embedded, giving the
retriever more semantic signal. Original text is preserved in metadata.

Reference: https://www.anthropic.com/news/contextual-retrieval
"""

import asyncio
from typing import Any

from langsmith.wrappers import wrap_openai
from openai import AsyncOpenAI

from app.core.config import settings
from app.ingestion.chunkers.base import BaseChunker, Chunk, ChunkStrategy
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Maximum document characters sent to the LLM per chunk call.
# gpt-4o-mini has a 128 K-token context window; 120 000 chars ≈ 30 000 tokens,
# leaving headroom for the chunk text and the system overhead.
MAX_DOC_CHARS = 120_000

# Prompt adapted from the Anthropic contextual retrieval paper.
# The LLM sees a bounded document window and one chunk; output is 1-2 sentences.
_CONTEXTUALIZE_PROMPT = """\
<document>
{document}
</document>

<chunk>
{chunk}
</chunk>

Give a short succinct context (1-2 sentences) to situate this chunk \
within the document for improved search retrieval. \
Answer only with the context, no preamble."""


class ContextualChunker(BaseChunker):
    """
    LLM-powered contextual enrichment decorator.

    Wraps any BaseChunker: delegates splitting to it, then enriches each
    chunk by prepending a concise LLM-generated context sentence. The
    enriched content (context + original text) is what gets embedded;
    the original text is preserved in metadata['raw_content'] and the
    generated prefix in metadata['context_prefix'].

    Only achunk() performs enrichment. The sync chunk() delegates to the
    base chunker without enrichment — callers that need enrichment must
    call await achunk().

    Costs per document:
    - One LLM chat completion per chunk (~150 output tokens with gpt-4o-mini)
    - Calls are run concurrently (bounded by ``concurrency``)
    - Only use when retrieval quality improvement justifies the LLM cost
    """

    def __init__(
        self,
        base_chunker: BaseChunker,
        model: str = "gpt-4o-mini",
        concurrency: int = 10,
        metadata_prefix: str = "",
    ) -> None:
        """
        Initialize contextual chunker.

        Args:
            base_chunker: Any BaseChunker for splitting (e.g., RecursiveChunker).
                Splitting strategy is delegated entirely to this object.
            model: OpenAI chat model for context generation. gpt-4o-mini
                gives a good quality/cost balance for short context summaries.
            concurrency: Maximum simultaneous LLM calls per document.
                Default 10 is safe for most OpenAI tier-1 rate limits.
            metadata_prefix: Optional prefix stored in metadata['context_prefix'].
        """
        # chunk_size/chunk_overlap are owned by base_chunker; pass minimal valid
        # values to satisfy BaseChunker validation.
        super().__init__(chunk_size=1, chunk_overlap=0, metadata_prefix=metadata_prefix)

        if concurrency <= 0:
            raise ValueError(
                f"concurrency must be a positive integer, got {concurrency!r}"
            )

        self._base_chunker = base_chunker
        self._model = model
        self._concurrency = concurrency
        self._client = wrap_openai(AsyncOpenAI(api_key=settings.openai_api_key))

        logger.debug(
            "ContextualChunker initialized",
            base_chunker=type(base_chunker).__name__,
            model=model,
            concurrency=concurrency,
        )

    def chunk(
        self,
        text: str,
        document_metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> list[Chunk]:
        """
        Split text using the base chunker without LLM enrichment.

        For contextual enrichment, use achunk() instead.
        This sync implementation is provided to satisfy the BaseChunker
        contract and for callers that do not need context prefixes.

        Args:
            text: Full document text.
            document_metadata: Document-level metadata.

        Returns:
            Chunks from the base chunker (no context prefix added).
        """
        return self._base_chunker.chunk(
            text=text,
            document_metadata=document_metadata,
            **kwargs,
        )

    async def achunk(
        self,
        text: str,
        document_metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> list[Chunk]:
        """
        Split text and enrich each chunk with an LLM-generated context prefix.

        Process:
        1. Delegate splitting to base_chunker.chunk().
        2. Fire up to ``concurrency`` parallel LLM chat completions.
        3. Each LLM call receives the full document + the chunk content.
        4. The 1-2 sentence response is prepended to chunk.content.
        5. Original content is preserved in metadata['raw_content'].
        6. Context prefix is stored in metadata['context_prefix'].
        7. chunk_strategy is overwritten to 'contextual'.

        Args:
            text: Full document text.
            document_metadata: Document-level metadata.

        Returns:
            Chunks with context-enriched content and updated metadata.

        Raises:
            ValueError: If the base chunker fails.
            Exception: Individual LLM failures propagate from asyncio.gather.
        """
        chunks = self._base_chunker.chunk(
            text=text,
            document_metadata=document_metadata,
            **kwargs,
        )

        if not chunks:
            return chunks

        # Precompute a single bounded document window once for all chunk calls.
        # This avoids redundant truncation work inside the hot path and ensures
        # we never exceed the model's context window regardless of document size.
        if len(text) > MAX_DOC_CHARS:
            logger.warning(
                "Document exceeds MAX_DOC_CHARS; truncating for contextual enrichment",
                original_chars=len(text),
                truncated_chars=MAX_DOC_CHARS,
            )
        document_window = text[:MAX_DOC_CHARS]

        logger.debug(
            "Starting contextual enrichment",
            chunk_count=len(chunks),
            model=self._model,
            document_chars=len(document_window),
        )

        sem = asyncio.Semaphore(self._concurrency)

        async def _enrich(chunk: Chunk) -> Chunk:
            async with sem:
                prompt = _CONTEXTUALIZE_PROMPT.format(
                    document=document_window,
                    chunk=chunk.content,
                )
                response = await self._client.chat.completions.create(
                    model=self._model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=150,
                    temperature=0,
                )
                raw_content_field = response.choices[0].message.content
                if raw_content_field is None:
                    logger.warning(
                        "OpenAI returned None content for contextual enrichment",
                        chunk_index=chunk.chunk_index,
                        finish_reason=response.choices[0].finish_reason,
                    )
                    context_prefix = ""
                else:
                    context_prefix = raw_content_field.strip()

                raw_content = chunk.content
                chunk.content = f"{context_prefix}\n\n{raw_content}"
                chunk.metadata["context_prefix"] = context_prefix
                chunk.metadata["raw_content"] = raw_content
                chunk.metadata["chunk_strategy"] = ChunkStrategy.CONTEXTUAL.value
                return chunk

        enriched = await asyncio.gather(*[_enrich(c) for c in chunks])

        logger.info(
            "Contextual enrichment completed",
            chunk_count=len(enriched),
        )

        return list(enriched)

    def get_strategy_name(self) -> ChunkStrategy:
        """Return the chunking strategy identifier."""
        return ChunkStrategy.CONTEXTUAL

