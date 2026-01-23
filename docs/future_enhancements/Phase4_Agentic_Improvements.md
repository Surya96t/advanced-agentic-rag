# Phase 4: Future Agentic Enhancements

**Date:** January 22, 2026  
**Status:** Ideas for Future Implementation  
**Priority:** Post-MVP Improvements

---

## Overview

This document captures potential enhancements to make the agentic RAG system more autonomous and intelligent. These improvements would increase the "agentic" nature of the system by adding LLM-based reasoning at key decision points.

**Current State:** Heuristic-based routing + score-based validation (fast, predictable)  
**Future State:** LLM-based reasoning at critical nodes (more intelligent, adaptive)

---

## Enhancement 1: LLM-Based Router

### Current Implementation (Heuristic)

**File:** `app/agents/nodes/router.py`

**Approach:**

- Uses keyword matching, word count, pattern detection
- Fast (<1ms), zero cost, deterministic
- Classifies as simple/complex/ambiguous

**Limitations:**

- May mis-classify ~5-10% of queries
- No semantic understanding
- Fixed rules, can't adapt to new patterns

### Proposed Enhancement

**Add LLM-based classification for better accuracy:**

```python
async def llm_router_node(state: AgentState) -> Command:
    """
    LLM-based query complexity analysis with reasoning.

    Benefits:
    - Semantic understanding of query intent
    - Adaptive to edge cases
    - Can explain classification reasoning

    Trade-offs:
    - Adds ~500ms latency
    - Costs ~$0.0005 per query
    - Requires error handling for LLM failures
    """

    prompt = f"""
    You are a query analysis expert. Analyze this user query and determine the best retrieval strategy.

    QUERY: {state["original_query"]}

    CLASSIFICATION OPTIONS:
    1. "simple" - Direct, single-concept query that can be searched as-is
       Examples: "How do I install Prisma?", "What is Clerk?"

    2. "complex" - Multi-concept query requiring decomposition into sub-queries
       Examples: "How do I integrate Clerk with Prisma?", "Setup auth and database"

    3. "ambiguous" - Vague query needing hypothetical document expansion
       Examples: "user sync issues", "database problems", "auth not working"

    Analyze the query considering:
    - Number of distinct concepts/frameworks mentioned
    - Specificity vs vagueness of language
    - Whether it requires multiple knowledge sources

    Return JSON:
    {{
        "complexity": "simple" | "complex" | "ambiguous",
        "reasoning": "Brief explanation of classification",
        "confidence": 0.0 to 1.0
    }}
    """

    response = await llm.ainvoke(prompt, temperature=0.1)
    classification = parse_json(response.content)

    # Determine routing based on LLM decision
    next_node = "retriever" if classification["complexity"] == "simple" else "query_expander"

    return Command(
        update={
            "query_complexity": classification["complexity"],
            "metadata": {
                "router_reasoning": classification["reasoning"],
                "router_confidence": classification["confidence"]
            }
        },
        goto=next_node
    )
```

**Implementation Notes:**

- Add fallback to heuristic router if LLM fails
- Track classification accuracy vs heuristics
- A/B test to measure impact on retrieval quality

**Estimated Impact:**

- 📈 Accuracy: +5-15% better classification
- 📉 Latency: +400-600ms per query
- 💰 Cost: +$0.0005 per query (~$5/10k queries)

---

## Enhancement 2: Hybrid Router Approach

### Best of Both Worlds

**Strategy:** Use heuristics first, LLM only for borderline cases

```python
async def hybrid_router_node(state: AgentState) -> Command:
    """
    Hybrid approach: Fast heuristics + LLM verification for edge cases.

    Benefits:
    - Fast path for clear-cut queries (90% of cases)
    - LLM reasoning for uncertain cases (10%)
    - Optimal cost/accuracy trade-off
    """

    query = state["original_query"]

    # Fast heuristic classification
    heuristic_result = analyze_query_complexity(query)
    confidence = calculate_confidence(query, heuristic_result)

    # If high confidence, use heuristic result
    if confidence > 0.85:
        logger.info(f"High confidence heuristic: {heuristic_result} ({confidence:.2f})")
        complexity = heuristic_result

    # If low confidence, verify with LLM
    else:
        logger.info(f"Borderline case, using LLM verification (confidence: {confidence:.2f})")
        llm_result = await llm_classify_query(query)
        complexity = llm_result["complexity"]

    next_node = "retriever" if complexity == "simple" else "query_expander"

    return Command(
        update={"query_complexity": complexity},
        goto=next_node
    )


def calculate_confidence(query: str, classification: str) -> float:
    """
    Calculate confidence in heuristic classification.

    Low confidence signals:
    - Word count near threshold (13-17 words)
    - Only 1 framework mentioned (could be simple or complex)
    - Mixed signals (has "and" but short query)
    """
    words = query.split()

    # Borderline word count
    if 13 <= len(words) <= 17:
        return 0.6

    # Framework count = 1 (ambiguous)
    if count_frameworks(query) == 1 and "with" in query.lower():
        return 0.7

    # Clear-cut cases
    return 0.95
```

**Estimated Impact:**

- 📈 Accuracy: +3-8% (LLM only for 10% of queries)
- 📉 Latency: +50ms average (90% fast, 10% slow)
- 💰 Cost: +$0.00005 per query (~$0.50/10k queries)

---

## Enhancement 3: LLM-Based Validator with Reasoning

### Current Implementation (Score-Based)

**File:** `app/agents/nodes/validator.py`

**Approach:**

- Calculates quality score from multiple checks
- Simple threshold: score >= 0.7 = pass
- Deterministic retry logic

**Limitations:**

- Can't reason about WHY quality is low
- Fixed retry strategy (just re-run)
- No adaptive refinement

### Proposed Enhancement

**Add LLM reasoning for validation and refinement:**

```python
async def llm_validator_node(state: AgentState) -> Command:
    """
    LLM-based validation with reasoning and adaptive refinement.

    Benefits:
    - Understands WHY response quality is low
    - Suggests specific refinements
    - Can request human feedback intelligently

    This is the MOST valuable agentic enhancement (reflection).
    """

    prompt = f"""
    You are a quality assessment expert. Evaluate this RAG system response.

    ORIGINAL QUERY: {state["original_query"]}

    GENERATED RESPONSE:
    {state["generated_response"]}

    RETRIEVED SOURCES:
    {format_sources(state["retrieved_chunks"])}

    EVALUATION CRITERIA:
    1. Source Attribution: Are sources cited correctly?
    2. Code Completeness: Is code complete and functional?
    3. Grounding: Is response based on retrieved sources (no hallucination)?
    4. Relevance: Does it answer the original question?
    5. Quality: Is it helpful, clear, and actionable?

    ASSESSMENT TASK:
    - Provide quality score (0.0 to 1.0)
    - List specific issues found
    - Recommend action: "approve", "retry_with_refinement", "request_human_feedback"
    - If retry, suggest HOW to refine the query for better results

    Return JSON:
    {{
        "quality_score": 0.0 to 1.0,
        "issues": ["issue1", "issue2", ...],
        "action": "approve" | "retry_with_refinement" | "request_human_feedback",
        "refinement_strategy": "Specific suggestion for improvement",
        "refined_query": "Improved query if retry recommended"
    }}
    """

    response = await llm.ainvoke(prompt, temperature=0.1)
    validation = parse_json(response.content)

    # Execute LLM's recommended action
    if validation["action"] == "approve":
        return Command(
            update={"validation_result": validation},
            goto=END
        )

    elif validation["action"] == "retry_with_refinement":
        if state["retry_count"] >= 2:
            # Max retries reached
            return Command(
                update={"validation_result": {**validation, "disclaimer": "Max retries reached"}},
                goto=END
            )
        else:
            # Retry with LLM's suggested refinement
            return Command(
                update={
                    "validation_result": validation,
                    "retry_count": state["retry_count"] + 1,
                    "original_query": validation["refined_query"],  # LLM suggests better query
                    "metadata": {
                        "refinement_strategy": validation["refinement_strategy"]
                    }
                },
                goto="query_expander"
            )

    else:  # request_human_feedback
        return Command(
            update={
                "validation_result": validation,
                "feedback_requested": True
            },
            goto=interrupt  # Pause for human input
        )
```

**Example LLM Reasoning:**

```json
{
  "quality_score": 0.65,
  "issues": [
    "No source citations in code examples",
    "Missing error handling in sample code",
    "Response doesn't address Clerk-specific setup"
  ],
  "action": "retry_with_refinement",
  "refinement_strategy": "Focus retrieval on Clerk authentication setup specifically, not general auth patterns",
  "refined_query": "How do I set up Clerk authentication middleware in a Next.js app with environment variables?"
}
```

**Estimated Impact:**

- 📈 Quality: +15-25% better responses (intelligent refinement)
- 📈 User Satisfaction: Higher (adaptive retry, not blind retry)
- 📉 Latency: +600-800ms for validation
- 💰 Cost: +$0.001 per validation (~$10/10k queries)

---

## Enhancement 4: Full ReAct Agent Pattern

### Most Autonomous Approach

**Replace structured workflow with tool-calling agent:**

```python
from langchain.agents import create_react_agent

# Define tools the agent can use
tools = [
    Tool(
        name="search_documentation",
        description="Search technical documentation for specific information",
        func=hybrid_search
    ),
    Tool(
        name="decompose_query",
        description="Break complex query into sub-queries",
        func=decompose_query
    ),
    Tool(
        name="generate_hypothetical",
        description="Generate hypothetical answer for vague queries",
        func=hyde_expansion
    ),
    Tool(
        name="web_search",
        description="Search the web for additional context",
        func=web_search
    ),
    Tool(
        name="validate_code",
        description="Check if generated code is syntactically correct",
        func=syntax_validator
    )
]

# Agent decides which tools to use and when
agent = create_react_agent(
    llm=ChatOpenAI(model="gpt-4"),
    tools=tools,
    prompt=REACT_PROMPT
)

# Run agent
result = await agent.ainvoke({
    "input": user_query,
    "chat_history": state["messages"]
})
```

**Benefits:**

- Full autonomy (agent explores solution space)
- Can combine tools creatively
- Adapts to novel situations

**Drawbacks:**

- Much slower (multiple LLM calls in loop)
- Unpredictable token usage
- Harder to debug/observe
- May not converge (infinite loops)

**Recommendation:** Only consider if structured workflow proves insufficient

---

## Enhancement 5: Dynamic Query Expansion Strategies

### Current Approach

**Fixed strategies:**

- Complex → Sub-query decomposition
- Ambiguous → HyDE expansion

### Proposed Enhancement

**Let LLM choose expansion strategy:**

```python
async def adaptive_expander_node(state: AgentState) -> dict:
    """
    LLM selects best expansion strategy based on query analysis.

    Strategies:
    - sub_query: Break into focused sub-questions
    - hyde: Generate hypothetical document
    - step_by_step: Break into sequential steps
    - comparative: Generate queries for each option to compare
    - none: Use original query (override router decision)
    """

    prompt = f"""
    Analyze this query and select the best expansion strategy:

    QUERY: {state["original_query"]}
    COMPLEXITY: {state["query_complexity"]}

    AVAILABLE STRATEGIES:
    1. sub_query - Break into 2-3 focused sub-questions
    2. hyde - Generate hypothetical answer document
    3. step_by_step - Break into sequential instruction steps
    4. comparative - Compare multiple options/frameworks
    5. none - Original query is already optimal

    Select strategy and generate expansions.
    """

    # LLM decides strategy and executes it
    result = await llm.ainvoke(prompt)

    return {"expanded_queries": result["queries"]}
```

---

## Implementation Roadmap

### Phase 4.1 (Current - MVP)

- ✅ Heuristic router
- ✅ Score-based validator
- ✅ Fixed expansion strategies
- **Goal:** Working end-to-end workflow

### Phase 4.2 (Post-MVP - Quick Wins)

- 🔄 Add hybrid router (heuristics + LLM for borderline)
- 🔄 Track classification accuracy metrics
- 🔄 A/B test router approaches

### Phase 4.3 (Enhancement - High Value)

- 🔄 LLM-based validator with reasoning
- 🔄 Adaptive refinement strategies
- 🔄 Human-in-the-loop with intelligent triggers

### Phase 4.4 (Advanced - If Needed)

- 🔄 Full LLM router (if heuristics prove insufficient)
- 🔄 Dynamic expansion strategy selection
- 🔄 ReAct agent pattern (if structured workflow insufficient)

---

## Cost-Benefit Analysis

| Enhancement     | Accuracy Gain | Latency Impact | Cost Impact  | Priority      |
| --------------- | ------------- | -------------- | ------------ | ------------- |
| Hybrid Router   | +3-8%         | +50ms avg      | +$0.5/10k    | **High**      |
| LLM Validator   | +15-25%       | +700ms         | +$10/10k     | **Very High** |
| Full LLM Router | +5-15%        | +500ms         | +$5/10k      | Medium        |
| ReAct Agent     | Variable      | +2-5s          | +$50-100/10k | Low           |

**Recommendation:** Implement Hybrid Router and LLM Validator first (best ROI)

---

## Metrics to Track

**Before implementing enhancements:**

1. Router classification accuracy (manual eval on 100 queries)
2. Validation quality correlation (score vs human rating)
3. Retry success rate (does retry improve quality?)
4. End-to-end latency (p50, p95, p99)
5. Cost per query

**After implementing enhancements:**

1. Compare all metrics above
2. A/B test user satisfaction
3. Measure cost increase vs quality gain

---

## References

- [LangGraph Conditional Routing Docs](https://langchain-ai.github.io/langgraph/concepts/)
- [ReAct Pattern Paper](https://arxiv.org/abs/2210.03629)
- [HyDE: Precise Zero-Shot Dense Retrieval](https://arxiv.org/abs/2212.10496)
- [Self-Reflection in LLM Agents](https://lilianweng.github.io/posts/2023-06-23-agent/)

---

**Last Updated:** January 22, 2026  
**Status:** Future Enhancements (Post-MVP)
