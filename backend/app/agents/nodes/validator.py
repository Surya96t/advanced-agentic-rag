"""
Validation and self-correction node.

This module validates generated responses for quality, completeness,
and grounding in retrieved sources. Implements retry logic for low-quality responses.
"""

import re
from typing import Literal

from langgraph.types import Command, interrupt

from app.agents.state import AgentState
from app.utils.logger import get_logger

logger = get_logger(__name__)


def check_source_attribution(response: str) -> tuple[bool, float]:
    """
    Check if response cites sources properly.

    Looks for citation patterns:
    - [Source: ...]
    - (Source: ...)
    - According to ...
    - As mentioned in ...

    Args:
        response: Generated response text

    Returns:
        Tuple of (has_citations, score)
        - has_citations: True if at least one citation found
        - score: 0.0 to 1.0 based on citation count (capped at 1.0)

    Example:
        >>> check_source_attribution("Install Clerk [Source: Clerk Docs]")
        (True, 1.0)
        >>> check_source_attribution("Install Clerk")
        (False, 0.0)
    """
    # Citation patterns
    patterns = [
        r'\[Source:.*?\]',
        r'\(Source:.*?\)',
        r'According to',
        r'As mentioned in',
        r'Based on',
        r'The documentation states',
    ]

    citation_count = 0
    for pattern in patterns:
        matches = re.findall(pattern, response, re.IGNORECASE)
        citation_count += len(matches)

    # Score: 0.0 if no citations, 1.0 if 1+ citations
    # (Could be more nuanced: 0.5 for 1, 1.0 for 2+)
    has_citations = citation_count > 0
    score = min(citation_count / 2.0, 1.0)  # 2+ citations = full score

    logger.debug(
        f"Source attribution check: {citation_count} citations found, score={score:.2f}")
    return has_citations, score


def check_code_completeness(response: str) -> tuple[bool, float]:
    """
    Check if code blocks are complete (no truncation or obvious errors).

    Checks for:
    - Unclosed braces: {, [, (
    - Truncation indicators: "...", "[...]", "(continued)"
    - Incomplete function definitions

    Args:
        response: Generated response text

    Returns:
        Tuple of (is_complete, score)
        - is_complete: True if no obvious incompleteness
        - score: 0.0 to 1.0 (penalty for each issue)

    Example:
        >>> check_code_completeness("function test() { return true; }")
        (True, 1.0)
        >>> check_code_completeness("function test() { return")
        (False, 0.5)
    """
    issues = []

    # Check for balanced braces in code blocks
    code_blocks = re.findall(r'```.*?```', response, re.DOTALL)
    for block in code_blocks:
        # Count braces
        brace_pairs = [('{', '}'), ('[', ']'), ('(', ')')]
        for open_char, close_char in brace_pairs:
            if block.count(open_char) != block.count(close_char):
                issues.append("unbalanced_braces")
                logger.debug(
                    f"Unbalanced '{open_char}{close_char}' detected: "
                    f"{block.count(open_char)} open, {block.count(close_char)} close")
                break  # One issue is enough

    # Check for truncation indicators
    truncation_patterns = [
        r'\.\.\.(?!\w)',  # ... not followed by word (ellipsis at end)
        r'\[.*?continued.*?\]',
        r'\(.*?truncated.*?\)',
    ]

    for pattern in truncation_patterns:
        if re.search(pattern, response, re.IGNORECASE):
            issues.append("truncation_indicator")
            logger.debug(f"Truncation pattern found: {pattern}")
            break  # Only count once

    # Calculate score (penalty for each issue type)
    issue_types = set(issues)
    penalty = len(issue_types) * 0.25  # Each issue type = -0.25
    score = max(1.0 - penalty, 0.0)

    is_complete = len(issues) == 0

    logger.debug(
        f"Code completeness check: {len(issues)} issues, score={score:.2f}")
    return is_complete, score


def check_grounding(response: str, chunks: list) -> tuple[bool, float]:
    """
    Check if response is grounded in retrieved chunks (simple keyword overlap).

    This is a simplified hallucination check using keyword overlap.
    A more sophisticated approach would use cosine similarity of embeddings.

    Args:
        response: Generated response text
        chunks: Retrieved SearchResult objects

    Returns:
        Tuple of (is_grounded, score)
        - is_grounded: True if significant overlap with chunks
        - score: 0.0 to 1.0 based on overlap percentage

    Example:
        >>> chunks = [SearchResult(content="Clerk provides authentication")]
        >>> check_grounding("Use Clerk for authentication", chunks)
        (True, 0.8)
    """
    if not chunks:
        # No chunks to ground in, can't validate
        logger.debug("No chunks available for grounding check")
        return False, 0.0

    # Extract keywords from response (simple word split, lowercase)
    response_words = set(word.lower()
                         for word in re.findall(r'\w+', response) if len(word) > 3)

    # Extract keywords from chunks
    chunk_text = " ".join(chunk.content for chunk in chunks)
    chunk_words = set(word.lower()
                      for word in re.findall(r'\w+', chunk_text) if len(word) > 3)

    # Calculate overlap
    if not response_words:
        return False, 0.0

    overlap = response_words.intersection(chunk_words)
    overlap_ratio = len(overlap) / len(response_words)

    # Threshold: >30% overlap = grounded
    is_grounded = overlap_ratio > 0.3
    score = min(overlap_ratio / 0.5, 1.0)  # 50% overlap = full score

    logger.debug(
        f"Grounding check: {overlap_ratio:.2%} overlap, score={score:.2f}")
    return is_grounded, score


def calculate_retrieval_confidence(chunks: list) -> float:
    """
    Calculate confidence based on retrieval scores.

    Uses average score of retrieved chunks as confidence metric.

    Args:
        chunks: Retrieved SearchResult objects with scores

    Returns:
        Confidence score 0.0 to 1.0

    Example:
        >>> chunks = [SearchResult(score=0.8), SearchResult(score=0.9)]
        >>> calculate_retrieval_confidence(chunks)
        0.85
    """
    if not chunks:
        return 0.0

    avg_score = sum(chunk.score for chunk in chunks) / len(chunks)

    logger.debug(
        f"Retrieval confidence: {avg_score:.2f} (avg of {len(chunks)} chunks)")
    return avg_score


def calculate_quality_score(
    attribution_score: float,
    completeness_score: float,
    grounding_score: float,
    retrieval_confidence: float,
) -> float:
    """
    Calculate weighted quality score from individual checks.

    Weights:
    - Source attribution: 30%
    - Code completeness: 25%
    - Grounding: 30%
    - Retrieval confidence: 15%

    Args:
        attribution_score: 0.0 to 1.0
        completeness_score: 0.0 to 1.0
        grounding_score: 0.0 to 1.0
        retrieval_confidence: 0.0 to 1.0

    Returns:
        Overall quality score 0.0 to 1.0
    """
    quality_score = (
        attribution_score * 0.30 +
        completeness_score * 0.25 +
        grounding_score * 0.30 +
        retrieval_confidence * 0.15
    )

    logger.info(
        f"Quality score: {quality_score:.2f} "
        f"(attr={attribution_score:.2f}, comp={completeness_score:.2f}, "
        f"ground={grounding_score:.2f}, retr={retrieval_confidence:.2f})"
    )

    return quality_score


def validator_node(state: AgentState) -> Command[Literal["query_expander", "__end__"]]:
    """
    Validator node that checks response quality and decides next action.

    Quality Checks:
    1. Source attribution (30% weight)
    2. Code completeness (25% weight)
    3. Grounding in sources (30% weight)
    4. Retrieval confidence (15% weight)

    Decision Logic:
    - quality_score >= 0.5: PASS → END (regardless of retry_count)
    - quality_score < 0.5 AND retry_count >= 2: MAX RETRIES → END (with disclaimer)
    - quality_score 0.4-0.5 AND retry_count < 2: BORDERLINE → retry via query_expander
      (optional human feedback via interrupt() when enabled)
    - quality_score < 0.4 AND retry_count < 2: FAIL → retry via query_expander

    Args:
        state: Current agent state with generated_response, retrieved_chunks, retry_count

    Returns:
        Command object with validation_result and routing decision

    Example:
        >>> state = {
        ...     "generated_response": "Install Clerk [Source: Docs]...",
        ...     "retrieved_chunks": [chunk1],
        ...     "retry_count": 0
        ... }
        >>> cmd = validator_node(state)
        >>> cmd.goto
        '__end__'  # or 'query_expander' for retry
    """
    logger.info("Validator node: Checking response quality")

    response = state.get("generated_response", "")
    chunks = state.get("retrieved_chunks", [])
    retry_count = state.get("retry_count", 0)

    # Run all quality checks
    has_attribution, attribution_score = check_source_attribution(response)
    is_complete, completeness_score = check_code_completeness(response)
    is_grounded, grounding_score = check_grounding(response, chunks)
    retrieval_confidence = calculate_retrieval_confidence(chunks)

    # Calculate overall quality score
    quality_score = calculate_quality_score(
        attribution_score=attribution_score,
        completeness_score=completeness_score,
        grounding_score=grounding_score,
        retrieval_confidence=retrieval_confidence,
    )

    # Collect issues
    issues = []
    if not has_attribution:
        issues.append("Missing source citations")
    if not is_complete:
        issues.append("Code appears incomplete or truncated")
    if not is_grounded:
        issues.append("Response may not be grounded in retrieved sources")
    if retrieval_confidence < 0.5:
        issues.append("Low retrieval confidence (weak source matches)")

    # Build validation result
    validation_result = {
        "passed": quality_score >= 0.7,
        "score": quality_score,
        "issues": issues,
        "checks": {
            "source_attribution": attribution_score,
            "code_completeness": completeness_score,
            "grounding": grounding_score,
            "retrieval_confidence": retrieval_confidence,
        }
    }

    # Decision logic
    # UPDATED: Lowered threshold from 0.7 to 0.5 to reduce retries and improve response time
    if quality_score >= 0.5:
        # PASS: Quality is acceptable
        logger.info(f"✅ Validation PASSED (score: {quality_score:.2f})")
        return Command(
            update={"validation_result": validation_result},
            goto="__end__"
        )

    elif retry_count >= 2:
        # MAX RETRIES: Stop trying, return best attempt
        logger.warning(
            f"⚠️ Max retries reached (score: {quality_score:.2f}), returning response with disclaimer")
        validation_result["disclaimer"] = (
            "Response quality is below threshold after 2 retries. "
            "This answer may be incomplete or less accurate than ideal."
        )
        return Command(
            update={"validation_result": validation_result},
            goto="__end__"
        )

    elif 0.4 <= quality_score < 0.5:
        # BORDERLINE: Optionally request human feedback
        # For now, we'll retry. To enable HITL, uncomment the interrupt() call
        logger.info(
            f"⚠️ Borderline quality (score: {quality_score:.2f}), retrying")

        # OPTIONAL: Human-in-the-loop for borderline cases
        # Uncomment to enable:
        # user_decision = interrupt({
        #     "reason": "borderline_quality",
        #     "score": quality_score,
        #     "issues": issues,
        #     "response_preview": response[:500]
        # })
        # if user_decision == "approve":
        #     return Command(update={"validation_result": validation_result}, goto="__end__")

        # For now: Auto-retry
        return Command(
            update={
                "validation_result": validation_result,
                "retry_count": retry_count + 1,
                "metadata": {
                    "retry_reason": f"Quality score {quality_score:.2f} below threshold 0.5",
                    "retry_attempt": retry_count + 1,
                }
            },
            goto="query_expander"  # Retry from expansion
        )

    else:
        # FAIL: Quality too low, retry
        logger.warning(
            f"❌ Validation FAILED (score: {quality_score:.2f}), retrying (attempt {retry_count + 1}/2)")
        return Command(
            update={
                "validation_result": validation_result,
                "retry_count": retry_count + 1,
                "metadata": {
                    "retry_reason": f"Quality score {quality_score:.2f} below threshold 0.5",
                    "retry_attempt": retry_count + 1,
                }
            },
            goto="query_expander"  # Retry from expansion
        )
