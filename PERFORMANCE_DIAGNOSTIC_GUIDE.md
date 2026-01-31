# Performance Diagnostic Guide

**Date:** January 30, 2026  
**Status:** Enhanced timing logs added ✅

---

## 🎯 What Was Done

Added comprehensive timing logs to all agent nodes to help diagnose performance bottlenecks:

### **Files Modified:**

1. ✅ `/backend/app/agents/nodes/router.py` - Added timing logs
2. ✅ `/backend/app/agents/nodes/query_expander.py` - Added timing logs
3. ✅ `/backend/app/agents/nodes/retriever.py` - Added detailed timing logs
4. ✅ `/backend/app/agents/nodes/generator.py` - Added timing logs
5. ✅ `/backend/app/agents/nodes/validator.py` - Added timing logs

### **New Files Created:**

6. ✅ `/backend/scripts/test_performance.py` - Performance test script
7. ✅ `/PERFORMANCE_OPTIMIZATION_PLAN.md` - Optimization strategy

---

## 🚀 How to Run Performance Test

### **Option 1: Using the Test Script (Recommended)**

```bash
# Terminal 1: Start backend (if not already running)
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Run performance test
cd backend
uv run python scripts/test_performance.py
```

This will:
- Run a test query through the full pipeline
- Display detailed timing logs for each node
- Show a results summary with metrics
- Log everything to console with clear visual separators

### **Option 2: Using the Frontend**

```bash
# Terminal 1: Start backend
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Start frontend
cd frontend
pnpm dev

# Terminal 3: Monitor logs
tail -f backend/server.log | grep -E "(⏱️|🚀|📚|✍️|✅|⚠️|❌)"
```

Then:
1. Open http://localhost:3000
2. Go to Chat page
3. Send a query
4. Watch the logs in Terminal 3

### **Option 3: Direct API Call**

```bash
# Get your JWT token from Clerk (login to frontend first)
# Then copy the token from browser DevTools -> Application -> Cookies

curl -X POST http://localhost:8000/api/v1/chat \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How to authenticate with Clerk?"
  }'
```

---

## 📊 What to Look For in Logs

The logs now show clear timing breakdowns with emojis for easy scanning:

```
================================================================================
🚀 ROUTER NODE - Starting query analysis
Query: How do I authenticate users with Clerk?...
Query classified as complex: How do I authenticate users with Clerk?...
✅ Routing to query_expander (complex query)
⏱️  ROUTER NODE completed in 0.05s
================================================================================

================================================================================
🔍 QUERY EXPANDER NODE - Starting query expansion
Query: How do I authenticate users with Clerk?...
Complexity: complex
Using sub-query decomposition strategy
⏱️  LLM decomposition took 1.23s
✅ Query expansion complete: 3 queries generated
⏱️  QUERY EXPANDER NODE completed in 1.25s
================================================================================

================================================================================
📚 RETRIEVER NODE - Starting multi-query hybrid search
Searching 3 queries for user test_user_integration_123
  Query 1: How does Clerk authentication work?...
  Query 2: Clerk setup steps?...
  Query 3: Best practices for authentication?...
Search config: top_k=10, min_similarity=0.3, hybrid_alpha=0.5
🔎 Searching query 1/3: How does Clerk authentication work?...
Embedding generation took 1.02s
Database search took 0.45s
Text search database query took 0.38s
✅ Query 1 returned 10 results in 1.85s
🔎 Searching query 2/3: Clerk setup steps?...
Embedding generation took 0.98s
Database search took 0.42s
Text search database query took 0.35s
✅ Query 2 returned 10 results in 1.75s
🔎 Searching query 3/3: Best practices for authentication?...
Embedding generation took 1.05s
Database search took 0.48s
Text search database query took 0.40s
✅ Query 3 returned 10 results in 1.93s
⏱️  All searches completed in 5.53s
Total results from all queries: 30
After deduplication: 18 unique chunks (took 0.02s)
Reranker not available, using hybrid search scores
⏱️  Sorting took 0.01s
✅ Retrieval complete
⏱️  RETRIEVER NODE completed in 5.56s
================================================================================

================================================================================
✍️  GENERATOR NODE - Synthesizing response from retrieved context
Query: How do I authenticate users with Clerk?...
Retrieved chunks: 5
Formatted context from 5 chunks (4532 chars)
Calling LLM for response generation...
✅ Generation complete
⏱️  LLM streaming took 4.32s
⏱️  GENERATOR NODE completed in 4.34s
================================================================================

================================================================================
✅ VALIDATOR NODE - Checking response quality
Response length: 1842 chars
Retrieved chunks: 5
Retry count: 0/2
Quality score: 0.68 (attr=0.80, comp=1.00, ground=0.55, retr=0.72)
✅ Validation PASSED (score: 0.68)
⏱️  VALIDATOR NODE completed in 0.12s
================================================================================
```

### **Key Metrics to Extract:**

1. **Router**: Should be <0.5s (just heuristics, no LLM)
2. **Query Expander**: 1-3s (LLM call for decomposition/HyDE)
3. **Retriever**: **THIS IS THE BOTTLENECK** (15-20s for 3 queries)
   - Embedding generation: 1-2s per query
   - Database search: 0.5-1s per query
   - Text search: 0.5-1s per query
   - Number of queries: 1-3 (affects total time)
4. **Generator**: 3-6s (LLM streaming)
5. **Validator**: <0.5s (quality checks)

### **Total Time Breakdown Example:**

```
Router:          0.05s   (  0.4%)
Query Expander:  1.25s   ( 10.6%)
Retriever:       5.56s   ( 47.2%)  ⚠️ BOTTLENECK
Generator:       4.34s   ( 36.8%)
Validator:       0.12s   (  1.0%)
Total:          11.32s
```

---

## 🔍 Analysis Questions

After running the test, answer these questions:

1. **How long did the RETRIEVER NODE take?** _____s
   - If >15s: Multiple queries + slow searches
   - If 5-10s: Moderate (2-3 queries)
   - If <5s: Fast (1 query or very fast DB)

2. **How many queries were searched?** _____
   - If 3: Query was classified as "complex" → decomposed
   - If 1: Query was classified as "simple" or "ambiguous"

3. **Embedding generation time per query?** _____s
   - If >2s: OpenAI API is slow (network latency)
   - If <1s: Normal

4. **Database search time per query?** _____s
   - If >2s: Supabase slow (check index usage)
   - If <1s: Normal

5. **Did validator trigger a retry?** Yes/No
   - If Yes: Add 10-15s for full retry cycle
   - If No: Single pass through pipeline

---

## 💡 Next Steps Based on Results

### **If Retriever >15s:**
→ Proceed with **Phase 1 Optimizations** in PERFORMANCE_OPTIMIZATION_PLAN.md:
- Reduce `top_k` from 10 to 5
- Enable parallel vector + text search
- Lower validator threshold

### **If Validator Retries:**
→ Adjust validator threshold from 0.5 to 0.4

### **If Query Expansion Always 3 Queries:**
→ Reduce to 2 queries or skip expansion for simple queries

---

## 📝 Share Your Results

After running the test, please share:

1. **Total time:** _____s
2. **Retriever time:** _____s
3. **Number of queries:** _____
4. **Retry count:** _____
5. **Screenshot or paste of timing logs**

Then we can determine the best optimization strategy! 🚀
