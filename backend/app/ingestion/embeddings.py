"""
Embeddings client for Integration Forge.

This module provides a production-grade wrapper around OpenAI's embedding API.
Handles batching, retry logic, rate limiting, and cost tracking for embedding
generation used in the RAG pipeline.

Design Philosophy:
- Reliability: Retry logic with exponential backoff
- Efficiency: Batch processing to minimize API calls
- Observability: Track costs, tokens, and failures
- Validation: Ensure vector dimensions match database schema
- Type Safety: Full async/await typing

Learning Note:
What are embeddings?
- Embeddings convert text → vectors (arrays of floats)
- Similar text → similar vectors (cosine similarity)
- Example: "user auth" and "login system" → close in vector space
- Used for semantic search: find relevant chunks by similarity

Why text-embedding-3-small?
- 1536 dimensions (fits HNSW index limit of 2000)
- Cost-effective: $0.02 per 1M tokens
- Fast: Lower latency than ada-002
- Quality: Good performance for RAG applications

Embedding Pipeline:
Text → Tokenize → OpenAI API → Vector (1536 floats) → Store in Supabase
"""

import asyncio
from typing import Any

from openai import AsyncOpenAI, OpenAIError, RateLimitError

from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# EMBEDDING CLIENT
# ============================================================================


class EmbeddingClient:
    """
    Async client for generating embeddings via OpenAI API.

    Handles batching, retries, rate limiting, and validation for embedding
    generation in the document ingestion pipeline.

    Attributes:
        model: OpenAI model name (default: text-embedding-3-small)
        dimensions: Vector dimensions (default: 1536)
        batch_size: Max texts per API call (default: 100)
        max_retries: Max retry attempts (default: 3)
        retry_delay: Initial retry delay in seconds (default: 1.0)

    Learning Note:
    Why async?
    - Non-blocking I/O: Don't wait for API while processing other chunks
    - Concurrency: Embed multiple batches in parallel
    - Performance: 10x faster than synchronous for large documents
    - Modern: FastAPI is async, this fits naturally

    Why batch processing?
    - Efficiency: 100 texts in 1 call vs 100 calls
    - Cost: Same token price, fewer API calls
    - Rate Limits: Fewer requests = less likely to hit limits
    - OpenAI Limit: Max 2048 texts per call (we use 100 for safety)
    """

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        dimensions: int = 1536,
        batch_size: int = 100,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        """
        Initialize embedding client.

        Args:
            model: OpenAI embedding model name
            dimensions: Vector dimension size (must match database schema)
            batch_size: Number of texts to embed per API call
            max_retries: Maximum retry attempts for failed requests
            retry_delay: Initial delay between retries (doubles each time)

        Raises:
            ValueError: If max_retries < 1 or other invalid parameters

        Learning Note:
        Why these defaults?
        - model: text-embedding-3-small is cost-effective and fast
        - dimensions: 1536 matches our Supabase schema and HNSW index
        - batch_size: 100 balances throughput vs memory
        - max_retries: 3 gives ~7 seconds total (1s + 2s + 4s)
        - retry_delay: 1s is respectful to API, doubles for backoff
        """
        # Validate parameters
        if max_retries < 1:
            raise ValueError(f"max_retries must be >= 1, got {max_retries}")
        if dimensions < 1:
            raise ValueError(f"dimensions must be >= 1, got {dimensions}")
        if batch_size < 1:
            raise ValueError(f"batch_size must be >= 1, got {batch_size}")
        if retry_delay <= 0:
            raise ValueError(f"retry_delay must be > 0, got {retry_delay}")

        self.model = model
        self.dimensions = dimensions
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Initialize async OpenAI client
        # Learning Note:
        # Why AsyncOpenAI instead of OpenAI?
        # - Non-blocking: Other code can run during API calls
        # - Scalability: Handle multiple requests concurrently
        # - FastAPI: Integrates seamlessly with async endpoints
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

        # Track usage for cost monitoring
        self._total_tokens = 0
        self._total_requests = 0
        self._failed_requests = 0

        logger.info(
            "EmbeddingClient initialized",
            model=self.model,
            dimensions=self.dimensions,
            batch_size=self.batch_size,
        )

    async def embed_texts(
        self,
        texts: list[str],
        show_progress: bool = False,
    ) -> list[list[float]]:
        """
        Generate embeddings for multiple texts with batching and retry logic.

        Process:
        1. Split texts into batches (100 per batch)
        2. For each batch:
           - Call OpenAI API with retry logic
           - Validate vector dimensions
           - Track token usage
        3. Combine results and return

        Args:
            texts: List of text strings to embed
            show_progress: Log progress for long operations

        Returns:
            List of embedding vectors (same order as input texts)

        Raises:
            ValueError: If texts list is empty or contains invalid data
            OpenAIError: If API calls fail after retries

        Learning Note:
        Why batching?
        - Without batching: 1000 texts = 1000 API calls
        - With batching: 1000 texts = 10 API calls (100 per batch)
        - Cost: Same tokens, fewer requests
        - Performance: Much faster due to reduced overhead
        - Rate Limits: Less likely to hit requests-per-minute limit

        Example:
        ```python
        client = EmbeddingClient()
        texts = ["hello world", "foo bar", "baz qux"]
        vectors = await client.embed_texts(texts)
        # vectors[0] → embedding for "hello world"
        # vectors[1] → embedding for "foo bar"
        # vectors[2] → embedding for "baz qux"
        ```
        """
        if not texts:
            raise ValueError("Cannot embed empty text list")

        # Remove empty strings and track original indices
        # Learning Note: OpenAI API rejects empty strings, so we filter them
        valid_texts = [(i, text)
                       for i, text in enumerate(texts) if text.strip()]
        if not valid_texts:
            raise ValueError("All texts are empty after stripping whitespace")

        logger.debug(
            "Starting embedding generation",
            total_texts=len(texts),
            valid_texts=len(valid_texts),
            batches=len(valid_texts) // self.batch_size + 1,
        )

        # Split into batches
        all_embeddings: list[list[float] | None] = [None] * len(texts)
        batches = [
            valid_texts[i: i + self.batch_size]
            for i in range(0, len(valid_texts), self.batch_size)
        ]

        # Process each batch
        for batch_idx, batch in enumerate(batches):
            if show_progress:
                logger.info(
                    "Processing batch",
                    batch_num=batch_idx + 1,
                    total_batches=len(batches),
                    batch_size=len(batch),
                )

            # Extract just the text strings for this batch
            batch_texts = [text for _, text in batch]

            # Embed batch with retry logic
            batch_embeddings = await self._embed_batch_with_retry(batch_texts)

            # Store embeddings at their original indices
            for (original_idx, _), embedding in zip(batch, batch_embeddings):
                all_embeddings[original_idx] = embedding

        # Verify all embeddings were generated
        if None in all_embeddings:
            missing_count = all_embeddings.count(None)
            raise ValueError(f"Failed to generate {missing_count} embeddings")

        logger.info(
            "Embedding generation completed",
            total_texts=len(texts),
            total_tokens=self._total_tokens,
            total_requests=self._total_requests,
        )

        return all_embeddings  # type: ignore[return-value]

    async def embed_single(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.

        Convenience method that wraps embed_texts for single text inputs.

        Args:
            text: Text string to embed

        Returns:
            Embedding vector as list of floats

        Raises:
            ValueError: If text is empty
            OpenAIError: If API call fails

        Learning Note:
        Why a separate method for single text?
        - Convenience: Cleaner API for single embeddings
        - Type Safety: Returns list[float] not list[list[float]]
        - Common Use Case: Often embed just one query at a time

        Example:
        ```python
        client = EmbeddingClient()
        query = "How do I authenticate users?"
        vector = await client.embed_single(query)
        # Use vector for similarity search
        ```
        """
        if not text.strip():
            raise ValueError("Cannot embed empty text")

        embeddings = await self.embed_texts([text])
        return embeddings[0]

    async def _embed_batch_with_retry(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """
        Embed a batch of texts with exponential backoff retry logic.

        Retries on:
        - Rate limit errors (RateLimitError)
        - Transient network errors
        - Server errors (5xx)

        Does NOT retry on:
        - Invalid API key (401)
        - Invalid input (400)
        - Quota exceeded (no point retrying)

        Args:
            texts: Batch of texts to embed

        Returns:
            List of embedding vectors

        Raises:
            OpenAIError: If all retries fail

        Learning Note:
        Why exponential backoff?
        - Retry 1: Wait 1 second (quick recovery for blips)
        - Retry 2: Wait 2 seconds (transient issues clearing)
        - Retry 3: Wait 4 seconds (give time for rate limits)
        - Total: ~7 seconds max wait time
        - Prevents: Overwhelming the API with rapid retries

        Why not retry on auth errors?
        - Auth Error: API key is wrong, retrying won't help
        - Quota Error: Account limit reached, retrying won't help
        - Input Error: Our data is bad, retrying won't help
        - Only retry: Transient network/server/rate-limit issues
        """
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                # Call OpenAI API
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=texts,
                    dimensions=self.dimensions,
                )

                # Extract embeddings from response
                embeddings = [item.embedding for item in response.data]

                # Validate dimensions
                for i, embedding in enumerate(embeddings):
                    if len(embedding) != self.dimensions:
                        raise ValueError(
                            f"Expected {self.dimensions} dimensions, "
                            f"got {len(embedding)} for text {i}"
                        )

                # Track usage
                self._total_tokens += response.usage.total_tokens
                self._total_requests += 1

                logger.debug(
                    "Batch embedding successful",
                    batch_size=len(texts),
                    tokens_used=response.usage.total_tokens,
                    attempt=attempt + 1,
                )

                return embeddings

            except RateLimitError as e:
                # Rate limit hit - wait and retry
                last_error = e
                self._failed_requests += 1

                wait_time = self.retry_delay * (2**attempt)
                logger.warning(
                    "Rate limit hit, retrying",
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    wait_time=wait_time,
                    error=str(e),
                )

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(wait_time)
                    continue

            except OpenAIError as e:
                # Other OpenAI error - check if retryable
                last_error = e
                self._failed_requests += 1

                # Don't retry auth or input errors
                # Check status code via structured attributes (not string matching)
                status_code = getattr(e, "status_code", None) or getattr(
                    e, "status", None)

                if status_code in (400, 401):
                    logger.error(
                        "Non-retryable OpenAI error",
                        error=str(e),
                        error_type=type(e).__name__,
                        status_code=status_code,
                    )
                    raise

                wait_time = self.retry_delay * (2**attempt)
                logger.warning(
                    "OpenAI error, retrying",
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    wait_time=wait_time,
                    error=str(e),
                    status_code=status_code,
                )

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(wait_time)
                    continue

            except Exception as e:
                # Unexpected error - log and raise
                last_error = e
                self._failed_requests += 1

                logger.error(
                    "Unexpected error during embedding",
                    error=str(e),
                    error_type=type(e).__name__,
                    batch_size=len(texts),
                )
                raise

        # All retries exhausted
        if last_error is None:
            # Safety check: should never happen with max_retries >= 1
            raise RuntimeError(
                "Retry loop exited without capturing an error. This indicates a bug."
            )

        logger.error(
            "All retries exhausted",
            max_retries=self.max_retries,
            last_error=str(last_error),
        )
        raise last_error

    def validate_dimensions(self, vector: list[float]) -> None:
        """
        Validate that vector has correct dimensions.

        Args:
            vector: Embedding vector to validate

        Raises:
            ValueError: If dimensions don't match expected

        Learning Note:
        Why validate dimensions?
        - Database Schema: Supabase expects exactly 1536 dimensions
        - HNSW Index: Index is created for 1536 dimensions
        - Type Safety: Catch bugs early (wrong model, API changes)
        - Data Integrity: Prevent storing invalid vectors

        What happens if dimensions mismatch?
        - Insert will fail with cryptic database error
        - Search will return wrong results
        - Index will be corrupted
        - Better to fail fast here with clear error message
        """
        if len(vector) != self.dimensions:
            raise ValueError(
                f"Vector dimension mismatch: expected {self.dimensions}, "
                f"got {len(vector)}"
            )

    def get_usage_stats(self) -> dict[str, Any]:
        """
        Get usage statistics for cost tracking and monitoring.

        Returns:
            Dictionary with usage stats:
            - total_tokens: Total tokens processed
            - total_requests: Total successful API requests
            - failed_requests: Total failed API requests
            - estimated_cost: Estimated cost in USD

        Learning Note:
        Why track usage?
        - Cost Awareness: Embeddings cost money ($0.02 per 1M tokens)
        - Budgeting: Track spending per document/user
        - Optimization: Identify expensive operations
        - Debugging: See if failures are common

        Cost Calculation:
        - text-embedding-3-small: $0.02 per 1M tokens
        - Example: 100K tokens = $0.002 (very cheap!)
        - For comparison: gpt-4 is ~$10 per 1M tokens (500x more)
        """
        estimated_cost = (self._total_tokens / 1_000_000) * 0.02

        return {
            "total_tokens": self._total_tokens,
            "total_requests": self._total_requests,
            "failed_requests": self._failed_requests,
            "estimated_cost_usd": round(estimated_cost, 4),
            "model": self.model,
            "dimensions": self.dimensions,
        }

    def reset_stats(self) -> None:
        """
        Reset usage statistics.

        Useful for testing or when starting a new ingestion job.
        """
        self._total_tokens = 0
        self._total_requests = 0
        self._failed_requests = 0
        logger.debug("Usage statistics reset")


# ============================================================================
# FACTORY FUNCTION
# ============================================================================


async def get_embedding_client() -> EmbeddingClient:
    """
    Factory function to create embedding client with default settings.

    Returns:
        Configured EmbeddingClient instance

    Learning Note:
    Why a factory function?
    - Dependency Injection: Easy to inject in FastAPI endpoints
    - Testing: Easy to mock for unit tests
    - Configuration: Single place to configure defaults
    - Flexibility: Can swap implementations (e.g., for different models)

    Usage in FastAPI:
    ```python
    @app.post("/embed")
    async def embed_text(
        text: str,
        client: EmbeddingClient = Depends(get_embedding_client)
    ):
        vector = await client.embed_single(text)
        return {"vector": vector}
    ```
    """
    return EmbeddingClient(
        model=settings.openai_embedding_model,
        dimensions=settings.openai_embedding_dimensions,
    )
