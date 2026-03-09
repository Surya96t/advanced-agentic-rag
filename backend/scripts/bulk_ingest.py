"""
Bulk document ingestion script for the enterprise corpus.

Processes a directory of text/PDF/Markdown files and ingests them into the
RAG system under a shared ``user_id`` (default: ``'system'``) so that all
authenticated users can search them via the two-tier RLS policy.

Primary use-case: loading the CUAD contract dataset (510 .txt files) into
the enterprise corpus.

Usage
-----
    uv run scripts/bulk_ingest.py --input-dir /path/to/full_contract_txt

Options
-------
    --input-dir   DIR     Directory of documents to ingest (required).
    --user-id     STR     Ownership sentinel (default: 'system').
    --concurrency INT     Max parallel ingest tasks (default: 5).
    --dry-run             List files that would be processed; write nothing.
    --chunker     STR     Chunking strategy: recursive | parent_child (default: recursive).

Examples
--------
    # Dry-run to verify file discovery
    uv run scripts/bulk_ingest.py --input-dir data/cuad --dry-run

    # Ingest with parent-child chunking, 3 concurrent workers
    uv run scripts/bulk_ingest.py --input-dir data/cuad --chunker parent_child --concurrency 3
"""

from __future__ import annotations

import asyncio
import argparse
import sys
from pathlib import Path

# Ensure repo root is on sys.path so ``app.*`` imports resolve correctly.
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.client import SupabaseClient
from app.database.repositories.chunks import ChunkRepository
from app.database.repositories.documents import DocumentRepository
from app.ingestion.chunkers import ParentChildChunker, RecursiveChunker
from app.ingestion.embeddings import get_embedding_client
from app.ingestion.pipeline import IngestionPipeline
from app.utils.logger import get_logger

logger = get_logger(__name__)

# File extensions recognised as ingestible documents
_ALLOWED_SUFFIXES = {".txt", ".md", ".pdf"}


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bulk-ingest documents into the enterprise corpus.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input-dir",
        required=True,
        type=Path,
        help="Directory containing documents to ingest.",
    )
    parser.add_argument(
        "--user-id",
        default="system",
        help="user_id assigned to all ingested documents. "
             "Use 'system' for enterprise corpus (two-tier RLS).",
    )
    def _positive_int(value: str) -> int:
        try:
            n = int(value)
        except ValueError:
            raise argparse.ArgumentTypeError(f"{value!r} is not an integer")
        if n <= 0:
            raise argparse.ArgumentTypeError(
                f"--concurrency must be >= 1, got {n}"
            )
        return n

    parser.add_argument(
        "--concurrency",
        type=_positive_int,
        default=5,
        help="Maximum number of documents to process in parallel (must be >= 1).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files that would be ingested without writing to the DB.",
    )
    parser.add_argument(
        "--chunker",
        choices=["recursive", "parent_child"],
        default="recursive",
        help="Chunking strategy to use.",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Per-file worker
# ---------------------------------------------------------------------------


async def _ingest_file(
    path: Path,
    pipeline: IngestionPipeline,
    user_id: str,
    semaphore: asyncio.Semaphore,
) -> str:
    """
    Ingest a single file using *pipeline*.

    Returns a short status string: ``"ingested"``, ``"skipped"`` (duplicate),
    or ``"failed: <reason>"``.
    """
    async with semaphore:
        try:
            file_bytes = await asyncio.to_thread(path.read_bytes)
        except OSError as exc:
            return f"failed: cannot read file — {exc}"

        try:
            doc, is_duplicate = await pipeline.ingest_document(
                file_bytes=file_bytes,
                filename=path.name,
                user_id=user_id,
                metadata={"document_title": path.stem},
            )
            return "skipped (duplicate)" if is_duplicate else "ingested"
        except Exception as exc:
            logger.error("Ingest failed", path=str(path), error=str(exc))
            return f"failed: {exc}"


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------


async def run(args: argparse.Namespace) -> None:
    input_dir: Path = args.input_dir
    user_id: str = args.user_id
    concurrency: int = args.concurrency
    dry_run: bool = args.dry_run
    chunker_name: str = args.chunker

    # ----------------------------------------------------------------
    # Discover files
    # ----------------------------------------------------------------
    if not input_dir.is_dir():
        logger.error("Input directory does not exist", path=str(input_dir))
        sys.exit(1)

    files = sorted(
        p for p in input_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in _ALLOWED_SUFFIXES
    )

    if not files:
        logger.warning("No supported files found", directory=str(input_dir))
        return

    logger.info(
        "Files discovered",
        count=len(files),
        directory=str(input_dir),
        suffixes=list(_ALLOWED_SUFFIXES),
    )

    if dry_run:
        for f in files:
            print(f"  [dry-run] {f}")
        print(f"\nTotal: {len(files)} file(s) — no changes written.")
        return

    # ----------------------------------------------------------------
    # Build pipeline
    # ----------------------------------------------------------------
    db = SupabaseClient.get_client()
    doc_repo = DocumentRepository(db)
    chunk_repo = ChunkRepository(db)
    embedding_client = await get_embedding_client()

    if chunker_name == "parent_child":
        chunker = ParentChildChunker(
            parent_chunk_size=1024,
            parent_chunk_overlap=200,
            child_chunk_size=256,
            child_chunk_overlap=32,
        )
    else:
        chunker = RecursiveChunker(chunk_size=1000, chunk_overlap=200)

    pipeline = IngestionPipeline(
        doc_repo=doc_repo,
        chunk_repo=chunk_repo,
        embedding_client=embedding_client,
        chunker=chunker,
    )

    logger.info(
        "Pipeline ready",
        user_id=user_id,
        chunker=chunker_name,
        concurrency=concurrency,
    )

    # ----------------------------------------------------------------
    # Concurrent ingestion
    # ----------------------------------------------------------------
    semaphore = asyncio.Semaphore(concurrency)
    tasks = [
        _ingest_file(path=f, pipeline=pipeline, user_id=user_id, semaphore=semaphore)
        for f in files
    ]

    results = await asyncio.gather(*tasks)

    # ----------------------------------------------------------------
    # Summary
    # ----------------------------------------------------------------
    ingested = sum(1 for r in results if r == "ingested")
    skipped = sum(1 for r in results if "skipped" in r)
    failed = sum(1 for r in results if "failed" in r)

    logger.info(
        "Bulk ingest complete",
        total=len(files),
        ingested=ingested,
        skipped=skipped,
        failed=failed,
    )
    print(
        f"\nBulk ingest complete: {ingested} ingested  "
        f"{skipped} skipped  {failed} failed  "
        f"(total {len(files)})"
    )

    if failed:
        # Print failure details
        for path, result in zip(files, results):
            if "failed" in result:
                print(f"  FAILED: {path.name} — {result}")


def main() -> None:
    args = _parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
