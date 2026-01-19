Yes, we are done with the high-level planning. We have defined **what** we are building, **how** the pieces fit together, and **which** tools we will use.

Here is your comprehensive **Architecture & Planning Document**. Save this file. It acts as the "Constitution" for your project.

---

# 🏗️ Architecture Design Document: Project "Integration Forge"

**Version:** 2.0
**Date:** January 18, 2026 (Updated with Advanced RAG Techniques)
**Status:** Approved for Implementation Phase

---

## 1. Executive Summary

**Project Name:** Integration Forge
**Core Concept:** A "Personal Stack Synthesizer" and Agentic RAG application.
**Problem:** Developers struggle to integrate disparate tools (e.g., Clerk + Prisma) because documentation is siloed.
**Solution:** A knowledge base where users ingest raw documentation. An AI Agent uses "Advanced RAG" to synthesize "glue code" by retrieving context from multiple sources, validating imports, and self-correcting errors.

---

## 2. High-Level System Architecture

We are adopting a **"Microservices Lite"** architecture to separate UI concerns (TypeScript) from AI Compute concerns (Python).

### The Flow

1.  **Frontend (Next.js):** Handles UI, Session Management, and File Uploads to Storage.
2.  **BFF Layer (Next.js API):** Proxies complex requests or handles lightweight data fetching.
3.  **Compute Backend (FastAPI):** The "Brain." Handles long-running agents, heavy parsing, and vector math.
4.  **Database (Supabase):** Central source of truth for Relations, Vectors, and Files.

```mermaid
[User] <--> [Next.js Client (Vercel)]
                    |
                    +--- (Auth / Session) ---> [Clerk]
                    |
                    +--- (File Uploads) -----> [Supabase Storage]
                    |
                    +--- (Chat Stream) ------> [FastAPI (Railway/Docker)]
                                                    |
                                                    +--- [LangGraph Agent]
                                                    |
                                                    +--- [Supabase DB (pgvector)]
```

---

## 3. Technology Stack

| Component         | Technology                     | Reasoning                                                                          |
| :---------------- | :----------------------------- | :--------------------------------------------------------------------------------- |
| **Frontend**      | **Next.js 14+ (App Router)**   | React Server Components, Vercel AI SDK integration, SEO.                           |
| **Styling**       | **Tailwind CSS + Shadcn/UI**   | Rapid UI development, accessible components.                                       |
| **Backend**       | **FastAPI (Python)**           | Native support for LangGraph/LangChain, async performance.                         |
| **Auth**          | **Clerk**                      | Best-in-class session management. (Next.js handles login; Python verifies tokens). |
| **Database**      | **Supabase (PostgreSQL)**      | Relational data + Vector Store (pgvector) in _one_ place. RLS enabled.             |
| **Storage**       | **Supabase Storage**           | S3-compatible blob storage for raw Markdown/PDF files.                             |
| **Orchestration** | **LangGraph (Python)**         | Enables cyclical, stateful agentic loops (Plan $\to$ Act $\to$ Reflect).           |
| **Observability** | **LangSmith**                  | Critical for tracing agent loops and debugging hallucination.                      |
| **Deployment**    | **Vercel (FE) + Railway (BE)** | Vercel for fast edge UI. Railway for long-running Dockerized Python apps.          |

---

## 4. Architectural Strategies

### A. Authentication & Security

- **Strategy:** "Stateless Token Handoff".
- **Flow:**
  1.  User logs in via Next.js (Clerk).
  2.  Next.js generates a Session Token (JWT).
  3.  Next.js passes this token in the `Authorization` header when calling FastAPI.
  4.  FastAPI middleware decodes the token using JWKS (JSON Web Key Set) from Clerk to verify identity and `user_id`.
- **Data Security:** **Row Level Security (RLS)** will be enforced at the Postgres level. A user can only select vectors where `user_id == current_user`.

### B. Ingestion Pipeline (The "ETL")

- **Strategy:** Async Processing with Multi-Stage Chunking.
- **Trigger:** User uploads a file.
- **Process:**
  1.  File saved to Blob Storage.
  2.  Backend downloads file.
  3.  **Advanced Chunking Pipeline:**
      - **Stage 1 (MVP):** `RecursiveCharacterTextSplitter` (1000 chars, 200 overlap) for baseline.
      - **Stage 2 (Advanced):** `SemanticChunker` using embedding similarity for natural breakpoints.
      - **Stage 3 (Production):** Parent-Child Indexing (small chunks for search, large chunks for context).
      - **Stage 4 (Code-Aware):** Detect code blocks, split by functions/classes using language-specific splitters.
  4.  **Contextual Enrichment:** Prepend document context to each chunk before embedding (Anthropic 2024 technique).
  5.  **Metadata Injection:** Tag with source, version, framework, section headers, code language.
  6.  **Dual Embedding:**
      - **Dense Vector:** `text-embedding-3-small` (1536 dim) for semantic search.
      - **Sparse Vector:** PostgreSQL `tsvector` for BM25 keyword search.
  7.  **Storage:** Upsert to `document_chunks` table with parent-child relationships.

### C. The Agentic Loop (The "Brain")

- **Strategy:** ReAct / Reflection Pattern with Query Expansion.
- **Nodes:**
  1.  **Query Expander:** Decomposes complex queries into sub-queries (e.g., "Clerk + Prisma" → ["Clerk webhooks", "Prisma user creation"]).
  2.  **Retriever:** 
      - **Hybrid Search:** Executes parallel dense (pgvector) + sparse (BM25) searches.
      - **RRF Fusion:** Combines top-50 results using Reciprocal Rank Fusion.
      - **Re-ranker:** Applies FlashRank (open-source) or Cohere Rerank to select top-5 most relevant chunks.
  3.  **Generator:** Writes the code/answer using retrieved context.
  4.  **Grader (Reflector):** Checks for syntax errors, hallucinations, and import correctness.
  5.  **Finalizer:** Streams response via SSE (Server-Sent Events) with citations.

---

## 5. Domain Modeling (Core Entities)

_Note: This is not the schema, but the conceptual objects._

1.  **Library/Source:** A grouping of documents (e.g., "Clerk V5 Documentation").
2.  **Document:** A specific file (e.g., `webhooks.md`).
3.  **Chunk:** A semantic piece of text with an embedding vector.
4.  **Chat Session:** A container for a conversation.
5.  **Message:** User or AI text.

---

## 6. Open Questions & placeholders

_These items must be resolved during implementation._

1.  **[?] Parsing Strategy for Code Blocks:**
    - _Question:_ If a code block is longer than the chunk size (e.g., a 200-line config file), how do we split it without breaking the syntax?
    - _Solution (Finalized):_ Use multi-stage chunking:
      - **MVP:** RecursiveCharacterTextSplitter with aggressive overlap (200 chars).
      - **Advanced:** Language-specific splitters that understand function/class boundaries.
      - **Production:** Parent-Child indexing where entire code block is parent, functions are children.
2.  **[?] Cost Management:**
    - _Question:_ How do we prevent a user from uploading a 500MB PDF and draining our OpenAI credits?
    - _Solution (Finalized):_ 
      - Hard limit: 5MB per file
      - 50 documents per user
      - 1M tokens per month per user
      - LangSmith automatic cost tracking
      - Monthly quota reset via cron job
3.  **[?] Latency Targets:**
    - _Question:_ The Agentic loop might take 45 seconds. Is this acceptable?
    - _Current Plan:_ Use optimistic UI updates ("Thinking about Clerk...", "Thinking about Prisma...") to keep the user engaged.
