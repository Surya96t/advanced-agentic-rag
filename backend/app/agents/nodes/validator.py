"""
Validation and self-correction node.

This module validates generated responses for quality and grounding using an
LLM with structured output, replacing fragile regex heuristics. Thresholds
are configurable via settings (validation_pass_threshold,
validation_retry_threshold, validation_max_retries).
"""

import asyncio
import time
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.types import Command
from pydantic import BaseModel, Field

from app.agents.state import AgentState
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Thresholds (sourced from settings so they can be overridden via .env)
# ─────────────────────────────────────────────────────────────────────────────
PASS_THRESHOLD = settings.validation_pass_threshold      # default 0.5
RETRY_THRESHOLD = settings.validation_retry_threshold    # default 0.4
MAX_RETRIES = settings.validation_max_retries            # default 2

# ─────────────────────────────────────────────────────────────────────────────
# LLM + structured-output model
# ─────────────────────────────────────────────────────────────────────────────

class LLMValidation(BaseModel):
    """Structured output returned by the LLM validator."""

    passed: bool = Field(
        description="True if the response is satisfactory overall"
    )
    score: float = Field(
        ge=0.0, le=1.0,
        description="Overall quality score from 0.0 (terrible) to 1.0 (excellent)"
    )
    issues: list[str] = Field(
        default_factory=list,
        description="Specific quality issues found (empty if none)"
    )
    reasoning: str = Field(
        description="Brief explanation of the quality assessment"
    )
    validation_skipped: bool = Field(
        default=False,
        description="True when the LLM validator was unavailable and result is a safe fallback"
    )


_validator_llm = ChatOpenAI(
    model=settings.openai_model,
    temperature=0.0,
    api_key=settings.openai_api_key,
).with_structured_output(LLMValidation)


# ─────────────────────────────────────────────────────────────────────────────
# LLM validation helper
# ─────────────────────────────────────────────────────────────────────────────

async def _llm_validate(
    query: str,
    response: str,
    context_preview: str,
) -> LLMValidation:
    """
    Ask the LLM to evaluate response quality against the query and context.

    Falls back to a passing LLMValidation on any error so the pipeline
    isn't blocked by validator failures.
    """
    system = (
        "You are a response quality evaluator. Given a user query, the context "
        "retrieved from a knowledge base, and an AI-generated answer, rate the "
        "answer quality on the following criteria:\n"
        "1. Accuracy / grounding — does the answer stay within the provided context?\n"
        "2. Completeness — does the answer fully address the query?\n"
        "3. Source citation — does the answer cite its sources where appropriate?\n"
        "4. Code quality — are any code blocks complete and correct?\n\n"
        "Return a score from 0.0 (completely wrong/unhelpful) to 1.0 (perfect).\n"
        f"A score >= {PASS_THRESHOLD} means the response passes. "
        "List specific issues if score is below that threshold."
    )
    user_msg = (
        f"QUERY:\n{query}\n\n"
        f"CONTEXT (first 800 chars of top sources):\n{context_preview[:800]}\n\n"
        f"RESPONSE:\n{response[:2000]}"
    )
    _msgs = [SystemMessage(content=system), HumanMessage(content=user_msg)]

    # Attempt the LLM call with one retry for transient errors (network, timeout).
    for attempt in range(2):
        try:
            result: LLMValidation = await _validator_llm.ainvoke(_msgs)
            return result
        except Exception as e:
            if attempt == 0:
                # First failure — wait briefly and retry once
                logger.warning(
                    f"LLM validator attempt {attempt + 1} failed: {type(e).__name__}; retrying"
                )
                await asyncio.sleep(1.0)
            else:
                # Second failure — log as error, return safe fallback
                logger.error(
                    "LLM validator unavailable after 2 attempts; defaulting to pass",
                    exc_info=True,
                )
                return LLMValidation(
                    passed=True,
                    score=PASS_THRESHOLD,
                    issues=[],
                    reasoning="Validator unavailable; response accepted by default.",
                    validation_skipped=True,
                )
    # Unreachable — satisfies type checker
    raise RuntimeError("Unexpected exit from retry loop")  # pragma: no cover


# ─────────────────────────────────────────────────────────────────────────────
# Node
# ─────────────────────────────────────────────────────────────────────────────

async def validator_node(state: AgentState) -> Command[Literal["query_expander", "__end__"]]:
    """
    Validator node — evaluates response quality with LLM structured output.

    Decision thresholds (configurable via .env):
    - score >= PASS_THRESHOLD (default 0.5)  → PASS → END
    - score < PASS_THRESHOLD & retries >= MAX_RETRIES → MAX RETRIES → END
    - score >= RETRY_THRESHOLD (default 0.4) → BORDERLINE → retry
    - score < RETRY_THRESHOLD                → FAIL → retry

    Args:
        state: AgentState with generated_response, retrieved_chunks, retry_count.

    Returns:
        Command routing to either ``__end__`` or ``query_expander``.
    """
    start_time = time.time()
    logger.info("⏱️  VALIDATOR NODE: Starting LLM-based quality evaluation")

    response = state.get("generated_response", "")
    chunks = state.get("retrieved_chunks", [])
    query = state.get("original_query", state.get("query", ""))
    retry_count = state.get("retry_count", 0)

    # Build a short context preview from the top-3 chunks
    context_preview = "\n---\n".join(
        chunk.content[:400] for chunk in chunks[:3]
    ) if chunks else "(no context retrieved)"

    # Call the LLM validator
    llm_result = await _llm_validate(query, response, context_preview)

    elapsed = time.time() - start_time

    validation_result = {
        "passed": llm_result.passed,
        "score": llm_result.score,
        "issues": llm_result.issues,
        "reasoning": llm_result.reasoning,
        "validation_skipped": llm_result.validation_skipped,
    }

    # ── Decision logic ────────────────────────────────────────────────────────
    if llm_result.score >= PASS_THRESHOLD:
        logger.info(
            f"⏱️  VALIDATOR NODE: Completed in {elapsed:.3f}s | "
            f"✅ PASSED (score={llm_result.score:.2f})"
        )
        return Command(
            update={"validation_result": validation_result},
            goto="__end__",
        )

    if retry_count >= MAX_RETRIES:
        logger.warning(
            f"⏱️  VALIDATOR NODE: Completed in {elapsed:.3f}s | "
            f"⚠️  Max retries reached (score={llm_result.score:.2f})"
        )
        validation_result["disclaimer"] = (
            f"Response quality below threshold after {MAX_RETRIES} retries. "
            "This answer may be incomplete or less accurate than ideal."
        )
        return Command(
            update={"validation_result": validation_result},
            goto="__end__",
        )

    # Below threshold and retries remain → retry
    logger.warning(
        f"⏱️  VALIDATOR NODE: Completed in {elapsed:.3f}s | "
        f"{'⚠️  Borderline' if llm_result.score >= RETRY_THRESHOLD else '❌ FAILED'} "
        f"(score={llm_result.score:.2f}), retrying (attempt {retry_count + 1}/{MAX_RETRIES})"
    )
    return Command(
        update={
            "validation_result": validation_result,
            "retry_count": retry_count + 1,
            "metadata": {
                "retry_reason": (
                    f"Quality score {llm_result.score:.2f} below threshold {PASS_THRESHOLD}"
                ),
                "retry_attempt": retry_count + 1,
            },
        },
        goto="query_expander",
    )
