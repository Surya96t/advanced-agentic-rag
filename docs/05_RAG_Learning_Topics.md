This is the correct move. A Monorepo is standard for this type of Full Stack + AI application. Since you have a template, I will skip the file-tree diagrams and focus entirely on the **Cognitive Architecture** (the logic inside the files).

Based on the latest engineering trends for late 2025/2026, here is your **Advanced RAG Strategy & Learning Report**. This document explains _what_ you are building, _why_ it is considered "Advanced," and exactly _what skills_ you will master by building it.

---

# 🧠 Advanced RAG & Agentic Strategy Report

**Project:** Integration Forge
**Architecture Level:** Senior / Principal AI Engineer
**Goal:** Build a system that doesn't just "search and retrieve" but "reasons and corrects."

---

## 1. The Ingestion Strategy: "Context-Aware Hierarchical Indexing"

**The Problem with Standard RAG:**
If you chunk a Markdown file solely by character count (e.g., 500 chars), you often slice a code block in half. The vector embedding of the second half (closing brackets) has no semantic meaning, so it never gets retrieved.

**The Advanced Solution:**
We will implement **Multi-Stage Chunking with Contextual Enrichment**.

### **Stage 1: MVP - Baseline Chunking**
1.  **RecursiveCharacterTextSplitter:** 1000 chars, 200 overlap
    - Purpose: Prove the pipeline works end-to-end
    - Fast to implement, industry-standard defaults

### **Stage 2: Semantic Boundary Detection**
1.  **Semantic Chunking:** Split by embedding similarity instead of character count
    ```python
    from langchain_experimental.text_splitter import SemanticChunker
    
    semantic_chunker = SemanticChunker(
        OpenAIEmbeddings(),
        breakpoint_threshold_type="percentile",
        breakpoint_threshold_amount=95
    )
    ```
2.  **Benefit:** Each chunk is a complete semantic unit (30-40% better retrieval)

### **Stage 3: Parent-Child Indexing (Small-to-Big Retrieval)**
1.  **The Pattern:**
    - **Small chunks (child):** Embedded for precise search
    - **Large chunks (parent):** Retrieved for LLM context
2.  **Database Implementation:**
    - `parent_chunk_id` foreign key in `document_chunks`
    - `chunk_type` enum: 'parent' or 'child'
3.  **Retrieval Flow:**
    - Search using child chunks (high precision)
    - Retrieve parent chunks (full context)
    - Send parent to LLM, cite child to user

### **Stage 4: Contextual Enrichment (Anthropic 2024)**
1.  **Context Injection:** Prepend document metadata before embedding
    ```python
    original = "Use the create() method to insert records."
    
    enriched = """
    [Document: Prisma ORM Guide | Section: Database Operations | Topic: Creating Records]
    
    Use the create() method to insert records.
    """
    ```
2.  **Benefit:** 25-35% improvement in retrieval precision
3.  **Why it works:** Embeddings now capture WHERE the chunk came from

### **Stage 5: Code-Aware Splitting**
1.  **Language-Specific Splitters:**
    ```python
    from langchain_text_splitters import RecursiveCharacterTextSplitter, Language
    
    code_splitter = RecursiveCharacterTextSplitter.from_language(
        language=Language.PYTHON,  # or JS, TS, etc.
        chunk_size=1000,
        chunk_overlap=100
    )
    ```
2.  **Split by:**
    - Function definitions
    - Class boundaries
    - Import statements
3.  **Metadata Injection:**
    ```json
    {
      "type": "code_block",
      "language": "typescript",
      "functions": ["auth()", "createUser()"],
      "imports": ["@clerk/nextjs", "prisma"]
    }
    ```

**🎓 What You Will Learn:**

- **AST Parsing:** How to parse text based on structure (Abstract Syntax Trees) rather than regex.
- **Enrichment Pipelines:** How to manipulate data _before_ it hits the Vector DB to increase retrieval accuracy by 20-30%.
- **Small-to-Big Retrieval:** The industry-standard pattern of decoupling "Search Units" (small) from "Generation Units" (big).
- **Semantic Boundary Detection:** Using embedding similarity to find natural chunk boundaries.
- **Contextual Retrieval:** Latest 2024 research from Anthropic for precision improvement.

---

## 2. The Retrieval Strategy: "Hybrid Ensemble with RRF"

**The Problem with Standard RAG:**
Vector search (Dense Retrieval) fails at exact matches. If you search for an error code "P2002" (Prisma Unique Constraint), a vector model might return documents about "Database Errors" in general, missing the specific solution.

**The Advanced Solution:**
We will build a **Hybrid Search Engine** using **Reciprocal Rank Fusion (RRF)**.

### **The Implementation:**

1.  **Dense Search (Semantic):** Query the vector store (`text-embedding-3-small`, pgvector) to find _conceptually_ similar docs.
    ```sql
    SELECT *, embedding <=> query_vector AS distance
    FROM document_chunks
    WHERE user_id = :user_id
    ORDER BY distance
    LIMIT 50;
    ```

2.  **Sparse Search (Keyword):** Query a Keyword Index (BM25 via PostgreSQL `tsvector`) to find _exact keyword_ matches.
    ```sql
    SELECT *, ts_rank_cd(search_vector, query) AS rank
    FROM document_chunks
    WHERE search_vector @@ to_tsquery(:query)
    AND user_id = :user_id
    ORDER BY rank DESC
    LIMIT 50;
    ```

3.  **RRF Fusion:** Combine the two lists. The RRF algorithm boosts documents that appear in _both_ lists to the top.
    - _Formula:_ $Score = \frac{1}{k + Rank_{vector}} + \frac{1}{k + Rank_{keyword}}$
    - _Constant k:_ Typically 60 (prevents division by zero, dampens rank differences)

4.  **Query Expansion (LLM-Based Decomposition):**
    ```python
    # User query: "Integrate Clerk webhooks with Prisma"
    
    # LLM decomposes into:
    sub_queries = [
        {
            "query": "Clerk webhook payload structure",
            "filter": {"tag": "clerk"}
        },
        {
            "query": "Prisma create user syntax",
            "filter": {"tag": "prisma"}
        }
    ]
    
    # Execute both searches in parallel
    # Combine results
    ```

**🎓 What You Will Learn:**

- **Information Retrieval Theory:** Understanding Dense vs. Sparse vectors and why they are complementary.
- **Search Algorithms:** Implementing RRF (the algorithm used by Google/Bing) from scratch or via library.
- **Database Tuning:** How to configure Postgres `tsvector` for production-grade keyword search alongside `pgvector`.
- **Query Decomposition:** Using LLMs to break complex queries into sub-queries.
- **Parallel Execution:** Running multiple searches concurrently for low latency.

---

## 3. The Refinement Strategy: "Cross-Encoder Re-ranking"

**The Problem with Standard RAG:**
Retrieving the "Top 5" chunks often includes 2 or 3 irrelevant ones (False Positives). These irrelevant chunks confuse the LLM, leading to hallucinations.

**The Advanced Solution:**
We introduce a **"Judge" Model** (Cross-Encoder) into the pipeline.

### **Phase 1: MVP - FlashRank (Open-Source)**
1.  **Broad Retrieval:** Fetch Top 50 documents using fast Hybrid Search.
2.  **The Re-ranker:** Pass 50 candidates + User Query into FlashRank.
3.  **The Verdict:** FlashRank scores every document from 0.0 to 1.0 based on _actual relevance_.
4.  **Implementation:**
    ```python
    from langchain.retrievers import ContextualCompressionRetriever
    from langchain_community.document_compressors import FlashrankRerank
    
    compressor = FlashrankRerank()
    compression_retriever = ContextualCompressionRetriever(
        base_compressor=compressor,
        base_retriever=vector_store.as_retriever(search_kwargs={"k": 50})
    )
    ```

### **Phase 2: Production - Cohere Rerank**
1.  **When to Upgrade:** After MVP is working, for better accuracy
2.  **Trade-off:** Paid API, but 10-15% better precision
3.  **Implementation:**
    ```python
    from langchain.retrievers.document_compressors import CohereRerank
    
    compressor = CohereRerank(model="rerank-english-v2.0")
    ```

**🎓 What You Will Learn:**

- **Bi-Encoders vs. Cross-Encoders:** You will learn that Bi-Encoders (Vectors) are fast but dumb, and Cross-Encoders are slow but smart. You will learn to orchestrate them together.
- **Latency Management:** Balancing the cost/time of re-ranking against the quality of answers.
- **Two-Stage Retrieval:** Broad recall (vector search) followed by precision re-ranking.
- **Open-Source vs. API Trade-offs:** Understanding when to use FlashRank vs Cohere.

---

## 4. The Agentic Loop: "Self-Correcting Code Generation"

**The Problem with Standard RAG:**
You ask for code. The LLM writes it. You run it. It errors. You are stuck.

**The Advanced Solution:**
We will use **LangGraph** to build a **State Machine** that mimics a human developer's workflow.

**The Workflow (The Graph):**

1.  **Node: Generator:** The Agent retrieves docs and writes the initial code.
2.  **Node: Validator (The Compiler):** The Agent analyzes its own code.
    - _Static Analysis:_ "Did I import `clerk` but use `clerk_client`?"
    - _Hallucination Check:_ "Is the function `prisma.createMany()` actually present in the retrieved documents?"
3.  **Edge: Conditional Logic:**
    - _If Valid:_ Stream to user.
    - _If Invalid:_ **Loop Back.** The Agent rewrites the code with the error context ("I previously tried X, but it failed because Y. Now I will try Z.").

**🎓 What You Will Learn:**

- **Graph Orchestration:** Moving beyond "Chains" (A $\to$ B $\to$ C) to "Graphs" (A $\to$ B $\leftrightarrows$ C).
- **State Management:** Passing a "Memory" object through the graph so the agent knows what it tried in previous loops.
- **Reflection Patterns:** The specific prompting technique that forces an LLM to critique its own work.

---

## Summary of Your Learning Path

By the end of this project, you will be able to answer these Senior Interview Questions:

1.  _"How do you handle the 'Lost in the Middle' phenomenon in RAG?"_ (Answer: **Re-ranking with FlashRank/Cohere**).
2.  _"How do you ensure your RAG system handles specific SKU numbers or Error Codes?"_ (Answer: **Hybrid Search with BM25**).
3.  _"How do you prevent your Agent from getting stuck in an infinite loop?"_ (Answer: **LangGraph State limits and max-retry logic**).
4.  _"How do you improve retrieval for nested code documentation?"_ (Answer: **Parent-Child Indexing with Contextual Enrichment**).
5.  _"What's the difference between RecursiveCharacterTextSplitter and SemanticChunker?"_ (Answer: **Character-based vs embedding-similarity boundaries**).
6.  _"How do you handle code blocks longer than your chunk size?"_ (Answer: **Language-specific splitters with function/class boundaries**).
7.  _"Explain the small-to-big retrieval pattern."_ (Answer: **Search with small chunks, retrieve parent chunks for context**).
8.  _"What is Reciprocal Rank Fusion and when would you use it?"_ (Answer: **Combining vector + keyword search results, formula: 1/(k+rank)**).
9.  _"How does query decomposition improve retrieval?"_ (Answer: **LLM breaks complex queries into sub-queries, searches in parallel**).
10. _"What is contextual enrichment and why does it improve precision by 35%?"_ (Answer: **Anthropic 2024 technique - prepend document context before embedding**).

---

## 🎯 Implementation Roadmap

### **Week 1-2: MVP (Baseline)**
- ✅ RecursiveCharacterTextSplitter (1000 chars, 200 overlap)
- ✅ Basic pgvector + tsvector hybrid search
- ✅ FlashRank re-ranking
- ✅ Simple LangGraph agent loop
- **Goal:** Prove end-to-end pipeline works

### **Week 3: Semantic Chunking**
- ✅ Implement SemanticChunker
- ✅ A/B test: RecursiveCharacter vs Semantic
- ✅ Measure retrieval accuracy improvement
- **Goal:** 30-40% better chunk quality

### **Week 4: Parent-Child Indexing**
- ✅ Add `parent_chunk_id` to database schema
- ✅ Implement small-to-big retrieval
- ✅ Update search logic to retrieve parents
- **Goal:** Better context for LLM without sacrificing search precision

### **Week 5: Contextual Enrichment**
- ✅ Implement context prefix injection
- ✅ A/B test: enriched vs non-enriched embeddings
- ✅ Measure precision improvement (target: 25-35%)
- **Goal:** Anthropic 2024 research implementation

### **Week 6: Code-Aware Splitting**
- ✅ Detect code blocks in documents
- ✅ Language-specific splitters (Python, TypeScript, JavaScript)
- ✅ Function/class boundary detection
- ✅ Rich metadata for code chunks
- **Goal:** Production-grade code documentation handling

### **Week 7: Query Expansion**
- ✅ LLM-based query decomposition
- ✅ Parallel sub-query execution
- ✅ Result merging and deduplication
- **Goal:** Handle multi-source integration queries

### **Week 8: Production Optimization**
- ✅ Upgrade to Cohere Rerank (compare vs FlashRank)
- ✅ Implement RLS policies
- ✅ LangSmith cost tracking integration
- ✅ Rate limiting and quota enforcement
- **Goal:** Production-ready system

---

## 📊 Success Metrics

Track these metrics to validate your advanced RAG implementation:

| Metric | Baseline (MVP) | Target (Advanced) | How to Measure |
|--------|----------------|-------------------|----------------|
| **Retrieval Precision@5** | 60-70% | 85-95% | Human eval: % of top-5 chunks relevant |
| **Chunk Boundary Quality** | 50% mid-sentence | 90% semantic boundaries | Manual review of 100 chunks |
| **Code Block Preservation** | 60% broken syntax | 95% intact | Test code blocks for syntax validity |
| **Cross-Document Queries** | 40% success | 80% success | "Clerk + Prisma" type queries |
| **Avg Query Latency** | <5s | <3s | P95 latency from LangSmith |
| **Cost per Query** | $0.05 | $0.03 | LangSmith cost tracking |

---

**Status:** Advanced RAG Strategy is **Complete**.
**Next Phase:** Create a new document `08_Implementation_Plan.md` with week-by-week tasks.
