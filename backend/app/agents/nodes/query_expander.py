"""
Query expansion node for complex and ambiguous queries.

This module implements two query expansion strategies:
1. Sub-query decomposition for complex queries
2. HyDE (Hypothetical Document Embeddings) for ambiguous queries
"""

import json
import time

from langchain_openai import ChatOpenAI

from app.agents.state import AgentState
from app.core.config import settings
from app.utils.logger import get_logger
from app.utils.observability import trace_node

logger = get_logger(__name__)

# LLM instance for query expansion
llm = ChatOpenAI(
    model=settings.openai_model,
    temperature=0.7,  # Higher temperature for creative expansion
    api_key=settings.openai_api_key,
)


# Prompt templates
DECOMPOSITION_PROMPT = """You are a research assistant. Break down this complex query into 2-3 focused sub-questions for document retrieval.

ORIGINAL QUERY: {query}

Generate sub-questions that:
- Cover different aspects of the main question
- Are specific and searchable within the user's uploaded documents
- Together help answer the original question

Return ONLY valid JSON in this exact format (no markdown, no explanation):
{{"sub_queries": ["query1", "query2", "query3"]}}

Example for "What are the key terms and obligations in the service agreement?":
{{"sub_queries": ["Key terms defined in the service agreement", "Obligations of each party", "Termination and renewal conditions"]}}"""


HYDE_PROMPT = """You are a research assistant. Generate a detailed hypothetical answer to this vague query to help with document search retrieval.

QUERY: {query}

Write a 200-word answer that includes:
- Specific terms and concepts related to the query
- Relevant keywords that would appear in documents about this topic
- Domain-appropriate vocabulary

This hypothetical answer will be used to find similar content in the user's documents.

Return ONLY the hypothetical answer text (no JSON, no preamble)."""


async def decompose_query(query: str) -> list[str]:
    """
    Decompose complex query into focused sub-queries using LLM.

    Strategy: Break multi-concept queries into 2-3 specific sub-questions
    that cover different aspects of the original query.

    Args:
        query: Complex query to decompose

    Returns:
        List of 2-3 sub-queries

    Raises:
        Exception: If LLM call fails or JSON parsing fails

    Example:
        >>> await decompose_query("How do I configure authentication with the database?")
        ["Authentication system configuration",
         "Database connection setup",
         "Integrating authentication with database"]
    """
    logger.info(f"Decomposing complex query: {query[:100]}...")

    try:
        # Call LLM for decomposition
        prompt = DECOMPOSITION_PROMPT.format(query=query)
        response = await llm.ainvoke(prompt)

        # Parse JSON response
        content = response.content.strip()

        # Remove markdown code blocks if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        result = json.loads(content)
        sub_queries = result.get("sub_queries", [])

        if not sub_queries:
            logger.warning("No sub-queries generated, using original query")
            return [query]

        logger.info(f"Generated {len(sub_queries)} sub-queries")
        return sub_queries

    except Exception as e:
        logger.error(f"Query decomposition failed: {e}")
        # Fallback: return original query
        return [query]


async def generate_hyde(query: str) -> str:
    """
    Generate hypothetical document for ambiguous queries (HyDE).

    Strategy: Create a detailed hypothetical answer that will be embedded
    and used for retrieval instead of the vague original query.

    Args:
        query: Ambiguous/vague query

    Returns:
        Hypothetical document text (200 words)

    Raises:
        Exception: If LLM call fails

    Example:
        >>> await generate_hyde("user sync issues")
        "When experiencing user synchronization issues, common causes include..."
        (200-word technical explanation)
    """
    logger.info(f"Generating hypothetical document for ambiguous query: {query[:100]}...")

    try:
        # Call LLM for HyDE generation
        prompt = HYDE_PROMPT.format(query=query)
        response = await llm.ainvoke(prompt)

        hypothetical_doc = response.content.strip()

        logger.info(f"Generated hypothetical document ({len(hypothetical_doc)} chars)")
        logger.debug(f"HyDE content: {hypothetical_doc[:200]}...")

        return hypothetical_doc

    except Exception as e:
        logger.error(f"HyDE generation failed: {e}")
        # Fallback: return original query
        return query


@trace_node("query_expander")
async def query_expander_node(state: AgentState) -> dict:
    """
    Query expansion node that selects and executes expansion strategy.

    Strategy selection based on query_complexity:
    - "complex" → Sub-query decomposition (2-3 focused queries)
    - "ambiguous" → HyDE (hypothetical document for embedding)

    Args:
        state: Current agent state with original_query and query_complexity

    Returns:
        State update dict with expanded_queries

    Example:
        >>> state = {
        ...     "original_query": "How do I configure authentication with the database?",
        ...     "query_complexity": "complex"
        ... }
        >>> result = await query_expander_node(state)
        >>> result["expanded_queries"]
        ["Authentication system configuration", "Database connection setup", "Integrating authentication with database"]
    """
    start_time = time.time()
    # Prefer retrieval_query (format instructions already stripped by router);
    # fall back to original_query when router was bypassed (e.g. direct invocation).
    query = state.get("retrieval_query") or state.get("original_query")
    if not query:
        logger.error("Missing query in state: retrieval_query or original_query")
        return {"expanded_queries": []}

    complexity = state.get("query_complexity", "simple")
    retry_count = state.get("retry_count", 0)

    logger.info(
        f"⏱️  QUERY_EXPANDER NODE: Starting {complexity} query expansion"
        f"{f' (retry {retry_count})' if retry_count else ''}"
    )

    # On retry (validator rejected the previous answer), always decompose even
    # for "simple" queries — the single-query search already failed, so trying
    # sub-queries gives the retriever a chance to find different chunks.
    if retry_count > 0 and complexity == "simple":
        logger.info("Retry detected for simple query — upgrading to sub-query decomposition")
        complexity = "complex"

    # Select strategy based on complexity
    if complexity == "complex":
        # Decompose into sub-queries
        logger.info("Using sub-query decomposition strategy")
        strategy_start = time.time()
        expanded = await decompose_query(query)
        strategy_time = time.time() - strategy_start
        logger.info(f"  ↳ Decomposition took {strategy_time:.3f}s")

    elif complexity == "ambiguous":
        # Generate hypothetical document
        logger.info("Using HyDE (hypothetical document) strategy")
        strategy_start = time.time()
        hypothetical_doc = await generate_hyde(query)
        strategy_time = time.time() - strategy_start
        logger.info(f"  ↳ HyDE generation took {strategy_time:.3f}s")
        # For HyDE, we use the hypothetical doc as a single "query"
        expanded = [hypothetical_doc]

    elif complexity == "simple":
        # Simple queries don't need expansion, pass through
        # Note: Router should send simple queries directly to retriever,
        # but if they somehow reach here, just use original query
        logger.info("Simple query detected, using original query without expansion")
        expanded = [query]

    else:
        # Unexpected complexity value
        logger.warning(f"Unknown complexity '{complexity}' in expander, using original query")
        expanded = [query]

    elapsed_time = time.time() - start_time
    logger.info(
        f"⏱️  QUERY_EXPANDER NODE: Completed in {elapsed_time:.3f}s | Generated {len(expanded)} queries"
    )

    return {"expanded_queries": expanded}
