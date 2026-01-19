# 🚀 The "Holy Trinity" RAG Portfolio

**Goal:** Build 3 production-grade AI applications demonstrating full-stack proficiency in Retrieval Augmented Generation. This is the overall goal but here we will be focusing only on PHASE 1.

## 🟢 Phase 1: The "Integration Forge" (Advanced Agentic RAG)

**Focus:** High-precision retrieval, complex ingestion, and agentic code synthesis.

- **Problem:** Developers struggle to integrate disparate tools (e.g., Clerk + Prisma + Neon) because documentation is siloed.
- **Solution:** A personal knowledge base where users "paste" docs. The AI acts as a Senior Architect, synthesizing "glue code" from multiple sources.
- **Key Architecture:**
  - **Ingestion:** Markdown-Aware Chunking + Metadata Injection (tagging stack versions).
  - **Retrieval:** **Hybrid Search** (Vector + Keyword) with **Query Expansion** (breaking 1 question into 2 searches).
  - **Agent Pattern:** **Self-Correction Loop** (Generate Code $\to$ Verify against Docs $\to$ Fix Imports $\to$ Final Answer).
- **Tech Stack:** Next.js, LangGraph, Pinecone/Supabase (pgvector), OpenAI/Anthropic.

### Application #1: "The Integration Forge" (Your Personal Docs Agent)

**The Concept:**
A knowledge management system where you paste "raw" documentation snippets (Markdown/Text) from various tools (Clerk, Neon, Prisma). The system doesn't just store them; it "learns" the syntax and allows you to ask: _"How do I create a user in Neon using Prisma after a Clerk webhook trigger?"_

**The "Advanced" Architecture Breakdown:**

#### 1. Advanced Ingestion: "Markdown-Aware Semantic Chunking"

We cannot blindly chop text every 500 characters. If we cut a code block in half, the LLM becomes stupid.

- **Technique:** **Markdown Header Splitting**.
  - We will split the pasted text by headers (`#`, `##`, `###`).
  - We keep code blocks (` ``` `) intact.
- **The "Contextual" Layer:**
  - When you paste the text, you tag it (e.g., `tech: clerk`, `version: v5`, `framework: nextjs`).
  - **Metadata Injection:** Before embedding, we inject this context into the chunk.
  - _Example Chunk:_ `[Context: Clerk Auth, Next.js App Router] To protect a route, use the auth() helper...`

#### 2. Retrieval: "Hybrid Search + Multi-Hop"

This is the critical part for "Integration" questions.

- **The Problem:** Asking about "Clerk and Prisma" requires finding chunks from _both_ unrelated documents.
- **The Solution: Query Expansion & Routing.**
  - User Query: "Integrate Clerk webhooks with Prisma."
  - **Router:** The LLM breaks this into:
    1.  "Clerk webhook payload structure" (Search Filter: `tag:clerk`)
    2.  "Prisma create user syntax" (Search Filter: `tag:prisma`)
  - **Parallel Execution:** It searches both "indexes" simultaneously.
  - **Hybrid Search:** It uses Vector search for "webhook" concepts and Keyword search for specific variable names like `user.create`.

#### 3. Agentic Workflow: "The Code Validator"

We don't just want text back; we want working code.

- **The Loop (LangGraph):**
  1.  **Retrieve:** Get the snippets from Clerk and Prisma.
  2.  **Generate:** The LLM attempts to write the integration code.
  3.  **Reflect/Critique:** The Agent looks at its own generated code and compares it _back_ to the retrieved docs.
      - _Check:_ "Did I use `auth()` (New SDK) or `getAuth()` (Old SDK)?"
      - _Check:_ "Does the retrieved Clerk doc mention specific import paths?"
  4.  **Refine:** If the imports are wrong, it rewrites the code before showing it to you.

---
