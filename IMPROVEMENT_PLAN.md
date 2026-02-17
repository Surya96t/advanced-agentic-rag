# RAG Improvements & Prompt Refactoring Plan

## 1. Goal
Transition the system from "Integration Forge" (a specialized integration assistant) to a **"Helpful Documentation Assistant"** using standard, high-quality RAG prompts. Additionally, clarify and optimize the retrieval scoring (RRF) to address concerns about "low scores."

## 2. Agentic Architecture Assessment
**Verdict:** **Advanced Agentic RAG** (Orchestrated Workflow)
- **Routing:** Uses `classifier` and `router` nodes to direct traffic.
- **Self-Correction:** Includes a `validator` loop to retry poor generations.
- **Planning:** Uses `query_expander` for complex query decomposition.
- **Not "Autonomous":** It follows a structured, deterministic StateGraph, which is preferred for reliability over open-ended autonomous agents.

## 3. Implementation Steps

### Phase 1: Prompt Engineering (Refactoring to "Helpful Documentation Assistant")

We will update the system prompts in `backend/app/agents/nodes/` to remove the "Integration Forge" persona and enforce strict RAG grounding.

| Component | File | Current Persona | New Persona |
|-----------|------|-----------------|-------------|
| **Generator** | `generator.py` | "Expert Integration Developer" (Focus: code synthesis, setup steps) | **"Helpful Documentation Assistant"** (Focus: answering from context, citing sources, neutral tone) |
| **Simple Answer** | `simple_answer.py` | "Helpful AI Assistant" (Friendly chit-chat) | **"Helpful Documentation Assistant"** (Polite, professional, guides user to technical topics) |
| **Query Expander** | `query_expander.py` | "Technical Documentation Expert" (Focus: decomposition) | **"Technical Research Assistant"** (Focus: breakdown for retrieval, neutral technical tone) |
| **Classifier** | `classifier.py` | "Integration Forge" specific routing | **Standard RAG Routing** (Simple vs. Complex vs. Ambiguous) |
| **Validator** | `validator.py` | Checks for "Integration Forge" style citations | **Standard Citation Check** (Ensure `[Source: ...]` exists, verify code block completeness) |

**New Generator System Prompt Strategy:**
```text
You are a helpful documentation assistant. Your task is to answer user questions strictly based on the provided context.

Context:
{context}

Guidelines:
1. Answer strictly based on the context. If the answer is not there, say "I cannot answer this based on the available documentation."
2. Cite your sources using [Source: Document Title].
3. Be concise and professional.
4. Do not make up information or use outside knowledge unless necessary to explain a concept found in the context.
```

### Phase 2: Retrieval Optimization (Scoring & RRF)

Address the "low score" perception and optimize for better recall.

1.  **Understand RRF Scoring:**
    *   Current algorithm: Reciprocal Rank Fusion ($Score = 1 / (60 + Rank)$).
    *   **Implication:** Max score is $\approx 0.033$. This is **normal** and mathematically correct for RRF, but confusing to users expecting 0.0-1.0 similarity.
    *   **Action:** We will add comments to `hybrid_search.py` explaining this range and potentially add a normalization step for logging/UI purposes ($Score \times 60$ or similar) to make it friendlier (0-1 range).

2.  **Tuning `limit`:**
    *   **Current:** `limit=10` (likely default).
    *   **Optimization:** Increase initial retrieval `limit` to **20 or 30** before re-ranking. This improves recall by giving the Reranker (`FlashRank`) more candidates to choose from.

3.  **Reranker Configuration:**
    *   **Current:** `rank-T5-flan` (FlashRank).
    *   **Action:** Verify configuration in `retriever.py`. Ensure we are passing the top 5-10 re-ranked results to the context window to maximize relevance.

## 4. Verification Plan

1.  **Manual Testing:**
    *   Query: "How does [Feature X] work?"
    *   **Check:** Response tone is neutral/helpful.
    *   **Check:** Citations are present `[Source: ...]`.
    *   **Check:** No "Integration Forge" mentions.
2.  **Retrieval Logs:**
    *   Inspect `backend/app/retrieval/hybrid_search.py` logs.
    *   Confirm we see RRF scores (e.g., `0.016`) and that the "low score" is just a visual artifact of the algorithm.
3.  **Agent Flow:**
    *   Ensure the `validator` still passes valid responses with the new prompt style.
