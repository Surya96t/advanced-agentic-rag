# Performance Optimization Plan - Integration Forge

**Date:** January 30, 2026  
**Current Query Time:** ~30 seconds  
**Target Query Time:** <10 seconds  
**Priority:** HIGH

---

## 🎯 Current Performance Profile

Based on code analysis, here's the execution flow and estimated timings:

```
User Query → Router (0.5s) → Query Expander (2s) → Retriever (15-20s) → Generator (5s) → Validator (0.5s)
                                                        ↑                                        ↓
                                                        └────────────── RETRY (if score < 0.5) ──┘
```

### Breakdown of 30-second query:

1. **Router**: ~0.5s (LLM call to classify query)
2. **Query Expander**: ~2s (LLM call to generate 2-3 sub-queries)
3. **Retriever**: **15-20s** ⚠️ BOTTLENECK
   - Embedding generation: 1-2s per query × 3 queries = 3-6s
   - Vector search (DB): 1-2s per query × 3 queries = 3-6s
   - Text search (DB): 1-2s per query × 3 queries = 3-6s
   - Deduplication: 0.5s
   - (Re-ranking disabled, so 0s)
4. **Generator**: ~5s (LLM call to generate response)
5. **Validator**: ~0.5s (quality checks)
6. **Retry penalty**: If validator fails, add 25-30s for full retry

---

## 🚀 Optimization Strategy (Tiered Approach)

### **Tier 1: Quick Wins (5-10x faster) - 1 hour**

#### ✅ Option A: Reduce `top_k` from 10 to 5
**Impact:** 40% faster retrieval (fewer results to fetch/process)  
**Trade-off:** May miss some relevant results, but likely minimal impact with good chunking  
**Files to modify:**
- `/backend/app/agents/nodes/retriever.py` (line 137)

```python
# BEFORE
search_config = SearchConfig(
    top_k=10,  # Get 10 results per query
    min_similarity=0.3,
    hybrid_alpha=0.5,
)

# AFTER
search_config = SearchConfig(
    top_k=5,  # Reduced from 10 → faster queries
    min_similarity=0.3,
    hybrid_alpha=0.5,
)
```

---

#### ✅ Option B: Skip query expansion for simple queries
**Impact:** 50% faster for simple queries (1 query instead of 3)  
**Trade-off:** Complex queries may get less comprehensive results  
**Files to modify:**
- `/backend/app/agents/nodes/router.py` (add complexity threshold)

**Implementation:**
Add a new router decision: "simple_direct" that skips query expansion and goes straight to retrieval with original query.

---

#### ✅ Option C: Increase validator threshold to 0.4 or disable retries
**Impact:** Eliminates 25-30s retry penalty in most cases  
**Trade-off:** Lower quality responses (but may still be acceptable)  
**Files to modify:**
- `/backend/app/agents/nodes/validator.py` (line 330)

```python
# OPTION C1: Increase threshold to accept more responses
if quality_score >= 0.4:  # Lowered from 0.5

# OPTION C2: Disable retries entirely (for testing)
if quality_score >= 0.3 or True:  # Always pass
```

---

### **Tier 2: Medium Impact (2-3x faster) - 2-3 hours**

#### 🔧 Option D: Enable parallel vector + text search
**Impact:** 30-40% faster retrieval (searches run concurrently)  
**Trade-off:** None (pure optimization)  
**Files to modify:**
- `/backend/app/retrieval/hybrid_search.py` (lines 165-177)

```python
# BEFORE (sequential)
vector_results = await self.vector_searcher.search(query, user_id, config)
text_results = await self.text_searcher.search(query, user_id, config)

# AFTER (parallel)
import asyncio
vector_results, text_results = await asyncio.gather(
    self.vector_searcher.search(query, user_id, config),
    self.text_searcher.search(query, user_id, config)
)
```

---

#### 🔧 Option E: Reduce query expansion from 3 to 2 sub-queries
**Impact:** 25% faster retrieval (fewer queries to search)  
**Trade-off:** Slightly less comprehensive coverage  
**Files to modify:**
- `/backend/app/agents/nodes/query_expander.py` (line 42)

```python
# BEFORE
Generate sub-questions that:
- Cover different aspects of the main question
- Are specific and searchable
- Together answer the original question

# AFTER
Generate 2 focused sub-questions (not 3) that:
...
```

---

### **Tier 3: Advanced (5-10x faster) - 4-6 hours**

#### 🚀 Option F: Cache embeddings in Redis
**Impact:** 80% faster embedding generation for repeat queries  
**Trade-off:** Requires Redis cache implementation  
**Complexity:** Medium  

**Implementation:**
1. Create embedding cache in Redis with TTL (1 hour)
2. Cache key: `embed:query:{hash(query)}`
3. Check cache before calling OpenAI API
4. Store embeddings in cache after generation

**Files to modify:**
- `/backend/app/ingestion/embeddings.py` (add cache layer)
- New file: `/backend/app/cache/embedding_cache.py`

---

#### 🚀 Option G: Implement query batching for multi-query search
**Impact:** 50% faster embedding generation (1 API call instead of 3)  
**Trade-off:** OpenAI API supports batch embeddings  
**Complexity:** Medium  

**Files to modify:**
- `/backend/app/agents/nodes/retriever.py` (batch embedding calls)
- `/backend/app/ingestion/embeddings.py` (add batch method)

---

### **Tier 4: Architectural Changes (10x+ faster) - 1-2 days**

#### 💡 Option H: Streaming partial results
**Impact:** Perceived latency reduced to <5s (first results shown immediately)  
**Trade-off:** Requires frontend UI changes  

**Implementation:**
- Stream chunks as they're retrieved (don't wait for all queries)
- Generator starts with partial chunks
- Validator runs incrementally

---

#### 💡 Option I: Pre-compute embeddings for common queries
**Impact:** Near-instant responses for common questions  
**Trade-off:** Requires query analytics and pre-computation  

---

## 📋 Recommended Implementation Order

### **Phase 1: Immediate (Today - 1 hour)**

1. ✅ **Reduce `top_k` from 10 to 5** (Option A)
2. ✅ **Lower validator threshold to 0.4** (Option C1)
3. ✅ **Add better timing logs** (see what's actually slow)

**Expected Result:** 15-20 second queries (50% improvement)

---

### **Phase 2: Short-term (This Week - 3 hours)**

4. ✅ **Enable parallel vector + text search** (Option D)
5. ✅ **Reduce query expansion to 2 queries** (Option E)

**Expected Result:** 10-12 second queries (70% improvement)

---

### **Phase 3: Medium-term (Next Week - 1 day)**

6. ✅ **Implement embedding cache** (Option F)
7. ✅ **Add query batching** (Option G)

**Expected Result:** 5-8 second queries (85% improvement)

---

## 🔍 Diagnostic Commands

### Check timing logs:
```bash
# Terminal 1: Start backend
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Monitor logs
tail -f backend/server.log | grep -E "(took|time|duration)"
```

### Test query and analyze:
```bash
# Send a test query and watch timing
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Authorization: Bearer YOUR_JWT" \
  -H "Content-Type: application/json" \
  -d '{"query": "How to authenticate with Clerk?"}'
```

### Expected log output:
```
Embedding generation took 1.23s
Database search took 2.45s
Text search database query took 1.87s
Retrieval complete: queries_searched=3, total_found=30, final_count=5
```

---

## ⚠️ Trade-offs Summary

| Option | Speed Gain | Quality Impact | Complexity |
|--------|-----------|----------------|------------|
| A: Reduce top_k | ⚡⚡⚡ 40% | ⚠️ Minor | ✅ Easy |
| B: Skip expansion | ⚡⚡⚡⚡ 50% | ⚠️⚠️ Moderate | ✅ Easy |
| C: Lower threshold | ⚡⚡⚡⚡⚡ 80% | ⚠️⚠️⚠️ Significant | ✅ Easy |
| D: Parallel search | ⚡⚡ 30% | ✅ None | ⚙️ Medium |
| E: 2 queries | ⚡⚡ 25% | ⚠️ Minor | ✅ Easy |
| F: Cache embeddings | ⚡⚡⚡⚡ 80% | ✅ None | ⚙️⚙️ Hard |
| G: Batch embeddings | ⚡⚡⚡ 50% | ✅ None | ⚙️ Medium |

---

## 🎯 Recommended Starting Point

**Start with Phase 1 (3 changes, 1 hour):**

1. Reduce `top_k=5`
2. Lower validator threshold to `0.4`
3. Enable parallel search

This should get you from **30s → 10-12s** with minimal quality impact.

Then evaluate if you need Phase 2/3 based on user feedback.

---

## 📝 Next Steps

1. **Run a test query** and share the timing logs
2. **Choose optimization tier** based on your speed/quality requirements
3. **I'll implement the changes** step-by-step with you
4. **Test and measure** improvement

**Which tier would you like to start with?**
- Quick Wins (Tier 1) - fastest implementation
- Medium Impact (Tier 2) - balanced approach
- All of Phase 1 - recommended starting point
