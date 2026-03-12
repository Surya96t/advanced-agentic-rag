"""
RAG Evaluation Pipeline using CUAD dataset + Ragas.

Loads contracts from the CUAD master_clauses.csv, ingests the matching PDFs
into Supabase (if not already present), runs each Q&A pair through the RAG
agent, scores with Ragas (context_precision, context_recall, faithfulness,
answer_relevancy), and writes results to the rag_evaluations table.

Usage:
    uv run scripts/run_eval.py \\
        --run-name "recursive_baseline" \\
        --strategy recursive \\
        --sample 50 \\
        --data-dir ../data/CUAD_v1

    uv run scripts/run_eval.py \\
        --run-name "parent_child_v1" \\
        --strategy parent_child \\
        --sample 50

Strategies: recursive (default), semantic, parent_child
"""

import argparse
import asyncio
import csv
import json
import sys
import time
from pathlib import Path
from typing import Any
from uuid import UUID

# Add backend root to path so `app.*` imports work when run via uv
sys.path.insert(0, str(Path(__file__).parent.parent))

# ---------------------------------------------------------------------------
# Third-party / stdlib imports — must come after sys.path insert
# ---------------------------------------------------------------------------
import pandas as pd
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from ragas import evaluate
from ragas.dataset_schema import EvaluationDataset, SingleTurnSample
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import (
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
    Faithfulness,
)

from app.agents.graph import run_agent
from app.core.config import settings
from app.database.client import SupabaseClient
from app.database.repositories.chunks import ChunkRepository
from app.database.repositories.documents import DocumentRepository
from app.ingestion.chunkers.parent_child import ParentChildChunker
from app.ingestion.chunkers.recursive import RecursiveChunker
from app.ingestion.chunkers.semantic import SemanticChunker
from app.ingestion.embeddings import EmbeddingClient, get_embedding_client
from app.ingestion.pipeline import IngestionPipeline
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EVAL_USER_ID = "eval_user"

# Maps category column name → natural-language question sent to the RAG agent
CATEGORY_QUESTIONS: dict[str, str] = {
    "Parties": "Who are the parties to this agreement?",
    "Agreement Date": "What is the date of this agreement?",
    "Effective Date": "When does this agreement become effective?",
    "Expiration Date": "When does this agreement expire?",
    "Renewal Term": "What is the renewal term of this agreement?",
    "Notice Period To Terminate Renewal": "What is the notice period required to terminate renewal of this agreement?",
    "Governing Law": "What is the governing law of this agreement?",
    "Most Favored Nation": "Does this agreement include a most favored nation clause?",
    "Competitive Restriction Exception": "Are there any exceptions to competitive restrictions in this agreement?",
    "Non-Compete": "Does this agreement contain a non-compete clause? If so, what are its terms?",
    "Exclusivity": "Is there an exclusivity clause in this agreement? If so, what are its terms?",
    "No-Solicit Of Customers": "Does this agreement contain a no-solicit of customers clause?",
    "No-Solicit Of Employees": "Does this agreement contain a no-solicit of employees clause?",
    "Non-Disparagement": "Does this agreement contain a non-disparagement clause?",
    "Termination For Convenience": "Can this agreement be terminated for convenience?",
    "ROFR/ROFO/ROFN": "Does this agreement include a right of first refusal, right of first offer, or right of first negotiation?",
    "Change Of Control": "What happens in a change of control under this agreement?",
    "Anti-Assignment": "Does this agreement include an anti-assignment clause?",
    "Revenue/Profit Sharing": "Is there a revenue or profit sharing arrangement in this agreement?",
    "Price Restrictions": "Are there price restrictions in this agreement?",
    "Minimum Commitment": "Is there a minimum commitment in this agreement?",
    "Volume Restriction": "Are there volume restrictions in this agreement?",
    "IP Ownership Assignment": "Who owns the intellectual property created under this agreement?",
    "Joint IP Ownership": "Is there joint IP ownership in this agreement?",
    "License Grant": "What license rights are granted under this agreement?",
    "Non-Transferable License": "Is the license granted in this agreement non-transferable?",
    "Affiliate License-Licensor": "Can the licensor grant licenses to affiliates under this agreement?",
    "Affiliate License-Licensee": "Can the licensee sublicense to affiliates under this agreement?",
    "Unlimited/All-You-Can-Eat-License": "Is an unlimited or all-you-can-eat license granted in this agreement?",
    "Irrevocable Or Perpetual License": "Is the license irrevocable or perpetual?",
    "Source Code Escrow": "Does this agreement include a source code escrow arrangement?",
    "Post-Termination Services": "Are there post-termination service obligations in this agreement?",
    "Audit Rights": "Does this agreement include audit rights?",
    "Uncapped Liability": "Is there uncapped liability in this agreement?",
    "Cap On Liability": "Is there a liability cap in this agreement? If so, what is it?",
    "Liquidated Damages": "Does this agreement include liquidated damages?",
    "Warranty Duration": "What is the warranty duration in this agreement?",
    "Insurance": "What insurance requirements are specified in this agreement?",
    "Covenant Not To Sue": "Does this agreement include a covenant not to sue?",
    "Third Party Beneficiary": "Are there any third party beneficiaries of this agreement?",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def build_chunker(strategy: str):
    """Instantiate the correct chunker for the given strategy name."""
    if strategy == "recursive":
        return RecursiveChunker(chunk_size=1000, chunk_overlap=200)
    if strategy == "semantic":
        return SemanticChunker()
    if strategy == "parent_child":
        return ParentChildChunker()
    raise ValueError(f"Unknown strategy: {strategy!r}. Choose: recursive, semantic, parent_child")


def ensure_eval_user(db) -> None:
    """Insert EVAL_USER_ID into the users table if it does not exist."""
    result = db.table("users").select("id").eq("id", EVAL_USER_ID).execute()
    if not result.data:
        db.table("users").insert({
            "id": EVAL_USER_ID,
            "email": "eval@eval.local",
        }).execute()
        logger.info(f"Created eval user: {EVAL_USER_ID}")
    else:
        logger.info(f"Eval user already exists: {EVAL_USER_ID}")


def load_cuad_samples(
    data_dir: Path,
    sample: int | None,
) -> list[dict[str, Any]]:
    """
    Load CUAD Q&A pairs where the corresponding PDF exists in data_dir.

    Returns a list of dicts with keys:
        filename, pdf_path, category, question, ground_truth
    """
    csv_path = data_dir / "master_clauses.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"master_clauses.csv not found at {csv_path}")

    df = pd.read_csv(csv_path)
    samples: list[dict[str, Any]] = []

    for _, row in df.iterrows():
        filename = str(row["Filename"])
        pdf_path = data_dir / filename
        if not pdf_path.exists():
            continue  # skip contracts whose PDF we don't have locally

        for category, question in CATEGORY_QUESTIONS.items():
            answer_col = f"{category}-Answer"
            if answer_col not in df.columns:
                continue
            ground_truth = str(row.get(answer_col, "") or "").strip()
            if not ground_truth or ground_truth.lower() in ("nan", "none", "[]", "['']"):
                continue  # skip empty answers

            samples.append({
                "filename": filename,
                "pdf_path": pdf_path,
                "category": category,
                "question": question,
                "ground_truth": ground_truth,
            })

    if sample:
        # Stratified by filename so we get even coverage across contracts
        per_contract = max(1, sample // len({s["filename"] for s in samples}))
        selected: list[dict[str, Any]] = []
        seen: dict[str, int] = {}
        for s in samples:
            count = seen.get(s["filename"], 0)
            if count < per_contract:
                selected.append(s)
                seen[s["filename"]] = count + 1
            if len(selected) >= sample:
                break
        samples = selected

    logger.info(f"Loaded {len(samples)} Q&A pairs from {len({s['filename'] for s in samples})} contracts")
    return samples


async def ingest_contract(
    pdf_path: Path,
    pipeline: IngestionPipeline,
    db,
) -> str | None:
    """
    Ingest a single PDF for EVAL_USER_ID. Returns the document_id as a string,
    or None if ingestion fails. Skips if already ingested (duplicate detection
    is handled inside IngestionPipeline via content hash).
    """
    try:
        file_bytes = pdf_path.read_bytes()
        doc, is_duplicate = await pipeline.ingest_document(
            file_bytes=file_bytes,
            filename=pdf_path.name,
            user_id=EVAL_USER_ID,
            metadata={"source": "cuad_eval", "eval_user": True},
        )
        status = "duplicate (skipped re-embedding)" if is_duplicate else "ingested"
        logger.info(f"  {pdf_path.name}: {status} — doc_id={doc.id}")
        return str(doc.id)
    except Exception as e:
        logger.error(f"  {pdf_path.name}: ingestion failed — {e}")
        return None


async def run_single_query(
    question: str,
    db,
) -> tuple[str, list[str], int]:
    """
    Run the RAG agent for a single question.

    Returns (generated_answer, context_texts, latency_ms).
    """
    start = time.time()
    response = await run_agent(
        query=question,
        user_id=EVAL_USER_ID,
        checkpointer=None,
    )
    latency_ms = int((time.time() - start) * 1000)

    generated_answer = response.content
    context_texts = [source.content for source in response.sources]

    return generated_answer, context_texts, latency_ms


def score_with_ragas(
    samples_batch: list[dict[str, Any]],
) -> list[dict[str, float]]:
    """
    Run Ragas evaluation on a batch of samples.

    Each item in samples_batch must have:
        question, answer, contexts (list[str]), ground_truth

    Returns a list of score dicts with keys:
        context_precision, context_recall, faithfulness, answer_relevancy, ragas_score
    """
    # Filter out samples with no retrieved contexts (agent error responses)
    valid = [s for s in samples_batch if s.get("contexts")]
    skipped = len(samples_batch) - len(valid)
    if skipped:
        logger.warning(f"Skipping {skipped} samples with empty contexts (agent errors)")
    if not valid:
        return [{"context_precision": 0, "context_recall": 0, "faithfulness": 0, "answer_relevancy": 0, "ragas_score": 0}]

    # Explicitly configure Ragas LLM + embeddings using our settings API key
    ragas_llm = LangchainLLMWrapper(
        ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key)
    )
    ragas_embeddings = LangchainEmbeddingsWrapper(
        OpenAIEmbeddings(model=settings.openai_embedding_model, api_key=settings.openai_api_key)
    )

    ragas_samples = [
        SingleTurnSample(
            user_input=s["question"],
            response=s["answer"],
            retrieved_contexts=s["contexts"],
            reference=s["ground_truth"],
        )
        for s in valid
    ]
    dataset = EvaluationDataset(samples=ragas_samples)

    metrics = [
        ContextPrecision(),
        ContextRecall(),
        Faithfulness(),
        AnswerRelevancy(),
    ]

    result = evaluate(dataset=dataset, metrics=metrics, llm=ragas_llm, embeddings=ragas_embeddings)
    result_df = result.to_pandas()

    scores: list[dict[str, float]] = []
    for _, row in result_df.iterrows():
        cp = float(row.get("context_precision", 0) or 0)
        cr = float(row.get("context_recall", 0) or 0)
        fa = float(row.get("faithfulness", 0) or 0)
        ar = float(row.get("answer_relevancy", 0) or 0)
        composite = (cp + cr + fa + ar) / 4
        scores.append({
            "context_precision": cp,
            "context_recall": cr,
            "faithfulness": fa,
            "answer_relevancy": ar,
            "ragas_score": composite,
        })

    # Pad back skipped samples with zero scores so indices align with samples_batch
    score_iter = iter(scores)
    aligned: list[dict[str, float]] = []
    for s in samples_batch:
        if s.get("contexts"):
            aligned.append(next(score_iter))
        else:
            aligned.append({"context_precision": 0, "context_recall": 0, "faithfulness": 0, "answer_relevancy": 0, "ragas_score": 0})
    return aligned


def write_results_to_db(
    db,
    run_name: str,
    strategy: str,
    samples: list[dict[str, Any]],
    scores: list[dict[str, float]],
) -> None:
    """Upsert all evaluation rows into the rag_evaluations table."""
    rows = []
    for sample, score in zip(samples, scores):
        rows.append({
            "run_name": run_name,
            "chunking_strategy": strategy,
            "model": settings.openai_model,
            "question": sample["question"],
            "ground_truth": sample["ground_truth"],
            "generated_answer": sample["answer"],
            "retrieved_chunks": json.dumps([
                {"content": c} for c in sample["contexts"]
            ]),
            "context_precision": score["context_precision"],
            "context_recall": score["context_recall"],
            "faithfulness": score["faithfulness"],
            "answer_relevancy": score["answer_relevancy"],
            "ragas_score": score["ragas_score"],
            "latency_ms": sample["latency_ms"],
            "contract_filename": sample["filename"],
        })

    # Batch insert in chunks of 50
    for i in range(0, len(rows), 50):
        db.table("rag_evaluations").insert(rows[i:i + 50]).execute()

    logger.info(f"Wrote {len(rows)} evaluation rows to rag_evaluations")


def print_summary(
    run_name: str,
    strategy: str,
    scores: list[dict[str, float]],
    db,
) -> None:
    """Print a summary table and compare to previous runs."""
    import statistics

    def mean(values: list[float]) -> float:
        return statistics.mean(values) if values else 0.0

    current = {
        "context_precision": mean([s["context_precision"] for s in scores]),
        "context_recall": mean([s["context_recall"] for s in scores]),
        "faithfulness": mean([s["faithfulness"] for s in scores]),
        "answer_relevancy": mean([s["answer_relevancy"] for s in scores]),
        "ragas_score": mean([s["ragas_score"] for s in scores]),
    }

    print("\n" + "=" * 60)
    print(f"  Eval Results — {run_name}  (strategy: {strategy})")
    print("=" * 60)
    print(f"  {'Metric':<25} {'Score':>8}  {'N':>5}")
    print(f"  {'-'*25} {'-'*8}  {'-'*5}")
    for metric, value in current.items():
        print(f"  {metric:<25} {value:>8.4f}  {len(scores):>5}")

    # Compare to previous runs for the same strategy (if any)
    try:
        prev = db.table("rag_evaluations") \
            .select("run_name, ragas_score, context_recall, context_precision, faithfulness, answer_relevancy") \
            .eq("chunking_strategy", strategy) \
            .neq("run_name", run_name) \
            .order("created_at", desc=True) \
            .limit(200) \
            .execute()

        if prev.data:
            prev_df = pd.DataFrame(prev.data)
            prev_grouped = prev_df.groupby("run_name").mean(numeric_only=True)
            print(f"\n  Prior runs (strategy={strategy}):")
            print(f"  {'Run':<30} {'ragas_score':>11} {'recall':>8} {'precision':>10}")
            print(f"  {'-'*30} {'-'*11} {'-'*8} {'-'*10}")
            for rn, row in prev_grouped.iterrows():
                delta = row["ragas_score"] - current["ragas_score"]
                delta_str = f"({'+' if delta >= 0 else ''}{delta:.4f})"
                print(f"  {str(rn):<30} {row['ragas_score']:>11.4f} {delta_str} {row['context_recall']:>8.4f} {row['context_precision']:>10.4f}")
    except Exception:
        pass  # comparison is best-effort

    print("=" * 60 + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main(args: argparse.Namespace) -> None:
    data_dir = Path(args.data_dir).resolve()
    logger.info(f"Starting eval: run_name={args.run_name!r}, strategy={args.strategy!r}, sample={args.sample}")
    logger.info(f"Data dir: {data_dir}")

    # --- Setup ---
    db = SupabaseClient.get_client()
    ensure_eval_user(db)

    # --- Build ingestion pipeline with chosen chunker ---
    chunker = build_chunker(args.strategy)
    embedder: EmbeddingClient = await get_embedding_client()
    doc_repo = DocumentRepository(db)
    chunk_repo = ChunkRepository(db)
    pipeline = IngestionPipeline(
        doc_repo=doc_repo,
        chunk_repo=chunk_repo,
        embedding_client=embedder,
        chunker=chunker,
    )

    # --- Load CUAD samples ---
    samples = load_cuad_samples(data_dir, sample=args.sample)
    if not samples:
        logger.error("No samples found. Check that PDF files exist in --data-dir.")
        sys.exit(1)

    # --- Ingest unique PDFs (skip if already ingested) ---
    unique_pdfs = {s["filename"]: s["pdf_path"] for s in samples}
    logger.info(f"Ingesting {len(unique_pdfs)} unique contracts...")
    for filename, pdf_path in unique_pdfs.items():
        await ingest_contract(pdf_path, pipeline, db)

    # --- Run RAG queries ---
    logger.info(f"Running {len(samples)} RAG queries...")
    for i, sample in enumerate(samples, 1):
        logger.info(f"  [{i}/{len(samples)}] {sample['category']} — {sample['filename'][:40]}")
        answer, contexts, latency_ms = await run_single_query(sample["question"], db)
        sample["answer"] = answer
        sample["contexts"] = contexts
        sample["latency_ms"] = latency_ms

    # --- Score with Ragas ---
    logger.info("Scoring with Ragas...")
    scores = score_with_ragas(samples)

    # --- Write to DB ---
    write_results_to_db(db, args.run_name, args.strategy, samples, scores)

    # --- Print summary ---
    print_summary(args.run_name, args.strategy, scores, db)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RAG Evaluation Pipeline (CUAD + Ragas)")
    parser.add_argument(
        "--run-name",
        required=True,
        help="Unique label for this eval run, e.g. 'recursive_baseline'",
    )
    parser.add_argument(
        "--strategy",
        default="recursive",
        choices=["recursive", "semantic", "parent_child"],
        help="Chunking strategy to use for ingestion (default: recursive)",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Max number of Q&A pairs to evaluate (default: all available)",
    )
    parser.add_argument(
        "--data-dir",
        default=str(Path(__file__).parent.parent.parent / "data" / "CUAD_v1"),
        help="Path to CUAD_v1 directory containing PDFs + master_clauses.csv",
    )
    args = parser.parse_args()
    asyncio.run(main(args))
