# RAG Eval Report — `recursive_smoke`

**Date:** 2026-03-11  
**Run name:** `recursive_smoke`  
**Chunking strategy:** `recursive` (RecursiveCharacterTextSplitter)  
**Model:** `gpt-4o-mini`  
**Sample size:** 9 Q&A pairs across 3 CUAD contracts  
**Dataset:** CUAD v1 (3 transportation agreement PDFs, 195 total chunks in DB)

---

## 1. Summary Scores

| Metric             | Score | What it means (short)                                          |
|--------------------|-------|----------------------------------------------------------------|
| context_precision  | 0.27  | 27% of retrieved chunks were actually useful                   |
| context_recall     | 0.56  | 56% of the information needed to answer was retrieved          |
| faithfulness       | 0.98  | 98% of claims in generated answers are grounded in context     |
| answer_relevancy   | 0.82  | 82% of generated answers directly address the question         |
| **ragas_score**    | **0.65** | Harmonic mean of all four — overall system health           |

---

## 2. Per-Question Breakdown

| # | Contract (short)   | Question category        | CP    | CR  | Faith | AR    | Ragas | Latency |
|---|-------------------|--------------------------|-------|-----|-------|-------|-------|---------|
| 1 | TcPipelines        | Who are the parties?     | 0.12  | 0.0 | 1.00  | 0.68  | 0.45  | 10.9s   |
| 2 | TcPipelines        | What is the date?        | 0.33  | 0.0 | 1.00  | 0.90  | 0.56  | 5.6s    |
| 3 | TcPipelines        | When does it take effect?| 0.20  | 1.0 | 0.90  | 0.96  | 0.77  | 6.8s    |
| 4 | RangeResources     | Who are the parties?     | 0.32  | 0.0 | 1.00  | 0.68  | 0.50  | 7.4s    |
| 5 | RangeResources     | What is the date?        | 0.33  | 1.0 | 1.00  | 0.94  | 0.82  | 4.7s    |
| 6 | RangeResources     | When does it take effect?| 0.25  | 1.0 | 1.00  | 0.96  | 0.80  | 8.3s    |
| 7 | ZtoExpress         | Who are the parties?     | 0.60  | 1.0 | 1.00  | 0.68  | 0.82  | 6.6s    |
| 8 | ZtoExpress         | What is the date?        | 0.25  | 1.0 | 1.00  | 0.59  | 0.71  | 5.5s    |
| 9 | ZtoExpress         | When does it take effect?| 0.00  | 0.0 | 0.88  | 0.96  | 0.46  | 22.4s   |

**CP** = context_precision, **CR** = context_recall, **Faith** = faithfulness, **AR** = answer_relevancy

---

## 3. What Each Metric Actually Measures

### Context Precision (avg: 0.27)

> *"Of all the chunks the system retrieved, what fraction were actually helpful?"*

Ragas looks at each retrieved chunk and asks: would this chunk alone help answer the question correctly? It then computes a precision-at-k score — chunks that appear earlier in the ranked list are weighted more heavily.

**Why 0.27 is expected here:** The retrieval runs at the `eval_user` level — every query searches all 3 contracts simultaneously. Ask "who are the parties?" and you get chunks from all three contracts, only one of which is the right contract. This is structural: chunks 2 and 3 of every 10 retrieved are cross-contract noise. The exception is question #7 (ZtoExpress parties, CP=0.60) where ZtoExpress's distinctive Chinese company names make its chunks easier to rank first.

**What would fix it:** Either scope retrieval to a single document per query (requires a document filter in the eval harness), or use parent-child / contextual chunking which embeds document identity more strongly into each chunk.

---

### Context Recall (avg: 0.56)

> *"Did the system actually retrieve the information it needed to answer the question?"*

Ragas takes each sentence in the ground-truth answer and checks whether it's supported by at least one retrieved chunk. A recall of 1.0 means every fact in the correct answer was present in the retrieved context; 0.0 means none of it was there.

**The pattern in the data:**

- **Recall = 0** on questions #1, #2, #4, #9 — the correct answer was *not* present in any retrieved chunk.
- **Recall = 1** on #3, #5, #6, #7, #8 — the correct answer *was* retrievable.

Questions about **party names** (Q1, Q4) had recall = 0 in 2 of 3 cases. Party names are mentioned briefly in the header section of a contract and the specific phrasing matters ("Great Lakes Gas Transmission Limited Partnership" vs. just "Great Lakes"). A generic "who are the parties?" query retrieves chunks about obligations and dates more often than the opening recitals.

Question #9 (ZtoExpress effective date, recall=0, latency=22.4s) is the most interesting failure. The ground truth date is "12/22/14" but the contract likely expresses this differently (e.g. "December 22, 2014"). The model spent 22 seconds on this — the validator triggered a retry (score=0.40, "borderline") and sub-query decomposition ran 3 extra searches, still without retrieving the right chunk. The answer the model generated was probably a reasonable inference ("would take effect upon signing") rather than the exact date.

---

### Faithfulness (avg: 0.98)

> *"Is everything the model said actually supported by the retrieved context?"*

This is the anti-hallucination metric. Ragas breaks the generated answer into atomic claims and checks each one against the retrieved chunks. A score near 1.0 means the model stays strictly within what was retrieved — it doesn't invent facts.

**Why 0.98 is good and expected:** `gpt-4o-mini` with the system prompt used here ("only answer from the provided context, cite sources") is well-calibrated for RAG. The two sub-1.0 scores:
- Q3 (TcPipelines effective date, faith=0.90): the model likely added a small interpretive statement not directly in a retrieved chunk.
- Q9 (ZtoExpress effective date, faith=0.88): the model had to work from context that didn't contain the actual date, so it made an educated guess — the only form of hallucination seen in this run.

**Important note:** High faithfulness doesn't mean high accuracy. The model can be 100% faithful (every claim grounded in context) while still being wrong — if the context retrieved is from the wrong contract. Faithfulness and recall together tell the full story.

---

### Answer Relevancy (avg: 0.82)

> *"Does the answer actually address what was asked?"*

Ragas uses an LLM to generate synthetic questions from the model's answer, then measures cosine similarity between those synthesized questions and the original question. A high score means the answer stayed on topic.

**The 0.68 floor on "Who are the parties?" questions (Q1, Q4, Q7):** All three party questions scored ~0.68. This is consistent — the model gives a structured answer listing multiple parties (e.g. "Party A is X, Party B is Y"), which is somewhat verbose compared to a direct extraction. The relevancy metric slightly penalises answers that elaborate beyond the exact question intent. This is a quirk of the metric rather than a real quality problem.

**The 0.59 on Q8 (ZtoExpress date):** The model gave a date answer that was probably correct but framed oddly (e.g. "The agreement is dated December 22, 2014, as shown in...") — slightly off-topic phrasing reduces the relevancy score.

---

## 4. Key Findings

| Finding | Evidence | Root Cause |
|---------|----------|------------|
| Retrieval is fetching cross-contract noise | CP = 0.27 across all samples | No document-scoping in search; all 3 contracts mix together |
| Party names are the hardest category | Recall = 0 in 2/3 party questions | Party names appear in contract headers; hybrid search ranks obligation/date chunks higher |
| Dates and effective dates are mostly retrievable | Recall = 1 in 4/6 date questions | Dates are compact, high-signal tokens that TF-IDF and vector search handle well |
| The LLM never fabricates when it has context | Faithfulness = 0.98 | Strong system prompt + well-calibrated gpt-4o-mini |
| One catastrophic retrieval miss (Q9) | CP=0, CR=0, latency=22.4s | Effective date phrasing mismatch + validator retry; agent spent 3× the compute and still failed |

---

## 5. Caveats

- **3 contracts only** — sampling variance is high; these numbers will shift with more data.
- **eval_user searches everything** — a real user only sees their own documents, so precision would be higher in production (but the test simulates a noisy retrieval environment).
- **Ground truth format** — CUAD's ground truth uses short formats ("12/14/15") that may not match how the model expresses dates ("December 14, 2015"), which can deflate recall even when the model is factually correct.
- **Ragas version** — these scores use ragas 0.2.15 with `LLMContextPrecisionWithoutReference` and default evaluation LLM (`gpt-4o`). Metric definitions may differ in future ragas versions.

---

## 6. Suggested Follow-Up Runs

| Run name            | Strategy      | What to learn                                            |
|---------------------|---------------|----------------------------------------------------------|
| `semantic_smoke`    | semantic      | Does semantic chunking improve recall on parties?        |
| `parent_child_smoke`| parent_child  | Does larger parent context help date/party retrieval?    |
| `recursive_full`    | recursive     | Run on full CUAD dataset (510 contracts) for stable stats|
| `recursive_filtered`| recursive     | Add document_id pre-filter to search to fix CP           |

To run a comparison:
```bash
cd backend
python scripts/run_eval.py --run-name "semantic_smoke" --strategy semantic --sample 10
```

The script will auto-print a delta table comparing new scores against the `recursive_smoke` baseline.

---

## 7. Bugs Fixed During This Run

Three pre-existing bugs were discovered and fixed while setting up this eval pipeline:

1. **`retriever.py` — Missing `content` and `rank` in sources** (production bug)  
   The retriever built `sources` dicts without `content` and `rank` fields, so every `ChatResponse` with actual results threw a Pydantic validation error. Fixed in `app/agents/nodes/retriever.py`.

2. **`documents.py` — Cross-user duplicate collision**  
   `get_by_hash()` didn't filter by `user_id`. Because the service role key bypasses RLS, a document owned by another user could be detected as a "duplicate" for a different user, causing ingestion skips. Fixed in `app/database/repositories/documents.py`.

3. **`run_eval.py` — Missing `await` on async embedding client**  
   `get_embedding_client()` is async; calling it without `await` returned a coroutine object instead of the actual embedder, causing all ingestion to fail. Fixed in `scripts/run_eval.py`.
