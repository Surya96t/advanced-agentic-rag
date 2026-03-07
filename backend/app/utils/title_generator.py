"""
Lightweight LLM call to generate a short thread title from the user's first message.

Runs as a background asyncio.Task concurrently with the main stream so it never
adds latency to token delivery.  Falls back to a simple truncation if the LLM call
fails or times out.
"""

from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

_TITLE_PROMPT = """\
You are a chat-title generator. Generate a short chat title (2-5 words) that \
summarises the user message below.
Output ONLY the title. No punctuation at the end, no quotes, no prefix.

Examples:
- "what is retrieval augmented generation" → Retrieval Augmented Generation
- "debug my python async code" → Python Async Debugging
- "help me write a cover letter" → Cover Letter Writing
- "explain transformers architecture" → Transformers Architecture Explained

User message: {message}"""


async def generate_title(user_message: str) -> str:
    """
    Generate a 2-5 word thread title using GPT-4o-mini.

    Falls back to a truncated version of the message on any error.

    Args:
        user_message: The first message sent by the user in this thread.

    Returns:
        A short title string (at most 100 characters).
    """
    try:
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            max_tokens=20,
            api_key=settings.openai_api_key,
        )
        response = await llm.ainvoke(_TITLE_PROMPT.format(message=user_message[:500]))
        title = response.content.strip()
        # Strip surrounding quotes that the model sometimes adds
        title = title.strip('"\'')
        return title[:100] if title else _truncate(user_message)
    except Exception:
        logger.warning("Title generation failed, falling back to truncation", exc_info=True)
        return _truncate(user_message)


def _truncate(message: str) -> str:
    cleaned = message.strip()
    return cleaned if len(cleaned) <= 50 else cleaned[:47] + "..."
