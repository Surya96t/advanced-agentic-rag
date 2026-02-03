# Conversational Agent Implementation Plan

## Executive Summary

This document outlines the comprehensive plan to transform the current RAG system into a **production-grade conversational agent** that handles multi-turn conversations, maintains context across messages, intelligently routes queries based on complexity, and manages context window limits using industry best practices from LangChain/LangGraph.

**Current State:**

- LangGraph checkpointer lifecycle is fixed (persists conversation state)
- Basic agent workflow: Router → Retrieval → Re-ranking → Generation
- SSE streaming to frontend works
- Citations are displayed

**Target State:**

- **Truly conversational**: Maintains context across turns, handles follow-ups, clarifications, and references to previous messages
- **Adaptive routing**: Short/simple questions skip retrieval; complex queries use full RAG pipeline
- **Context-aware**: Manages conversation history with automatic summarization and message trimming
- **Production-ready**: Robust error handling, graceful degradation, comprehensive logging

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Phase 1: Conversational Memory](#phase-1-conversational-memory)
3. [Phase 2: Adaptive Query Classification](#phase-2-adaptive-query-classification)
4. [Phase 3: Context Window Management](#phase-3-context-window-management)
5. [Phase 4: Frontend Enhancements](#phase-4-frontend-enhancements)
6. [Phase 5: Testing & Observability](#phase-5-testing--observability)
7. [Implementation Timeline](#implementation-timeline)
8. [Appendix: Best Practices Reference](#appendix-best-practices-reference)

---

## Architecture Overview

### Current Agent Graph

```
START → Router → Retrieval → Re-ranking → Generator → END
```

### Proposed Conversational Agent Graph

```
START → Conversation Context Loader → Query Classifier → [Routing Logic]
                                                          ├─→ Simple Path → Direct Answer → END
                                                          └─→ Complex Path → Query Expansion
                                                                           → Retrieval
                                                                           → Re-ranking
                                                                           → Generator
                                                                           → END
```

### Key Components

1. **Conversation Context Loader**: Loads and trims conversation history from checkpointer
2. **Query Classifier**: Determines if query is simple/complex, conversational/standalone
3. **Adaptive Router**: Routes to appropriate path based on classification
4. **Context Manager**: Handles message history, summarization, and trimming
5. **Memory Store**: PostgresCheckpointer (already in place)

---

## Phase 1: Conversational Memory

### 1.1 Update State Schema

**File:** `backend/app/agents/state.py`

**Current State:**

```python
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    query: str
    retrieved_documents: List[Dict[str, Any]]
    reranked_documents: List[Dict[str, Any]]
    final_answer: str
    # ... other fields
```

**Enhanced State:**

```python
class AgentState(TypedDict):
    # Message history (managed by add_messages reducer)
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # Current query processing
    query: str
    original_query: str  # NEW: Preserve original user query

    # Query classification (NEW)
    query_type: str  # "simple" | "complex" | "conversational"
    needs_retrieval: bool  # True if requires RAG pipeline

    # Conversation context (NEW)
    conversation_summary: str  # Summary of older messages
    context_window_tokens: int  # Current token count

    # Retrieval pipeline
    retrieved_documents: List[Dict[str, Any]]
    reranked_documents: List[Dict[str, Any]]

    # Generation
    final_answer: str

    # Metadata
    user_id: str
    session_id: str
    pipeline_path: str  # NEW: "simple" | "complex" for debugging
```

### 1.2 Add Conversation Context Loader Node

**File:** `backend/app/agents/nodes/context_loader.py` (NEW)

**Purpose:** Load conversation history, trim if needed, and prepare context for classification

**Implementation:**

```python
from typing import Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from app.agents.state import AgentState
from app.core.config import settings
import tiktoken

async def load_conversation_context(state: AgentState) -> Dict[str, Any]:
    """
    Load and prepare conversation context.

    Steps:
    1. Get all messages from state (checkpointer loads them)
    2. Count tokens in message history
    3. If exceeds limit, trim older messages
    4. Add system message with conversation context

    Returns:
        Updated state with trimmed messages and context summary
    """
    messages = list(state["messages"])

    # Count tokens (use tiktoken for OpenAI models)
    encoding = tiktoken.encoding_for_model(settings.openai_model)
    total_tokens = sum(len(encoding.encode(msg.content)) for msg in messages if hasattr(msg, 'content'))

    # If over limit, trim and summarize
    if total_tokens > settings.max_conversation_tokens:
        trimmed_messages, summary = await trim_and_summarize(messages, encoding)
        return {
            "messages": trimmed_messages,
            "conversation_summary": summary,
            "context_window_tokens": sum(len(encoding.encode(msg.content)) for msg in trimmed_messages)
        }

    return {
        "context_window_tokens": total_tokens,
        "conversation_summary": ""
    }

async def trim_and_summarize(messages: List[BaseMessage], encoding) -> tuple[List[BaseMessage], str]:
    """
    Trim old messages and create summary.

    Strategy:
    1. Keep system message (if any)
    2. Keep last N messages (recent context)
    3. Summarize middle messages
    """
    # Always keep system message
    system_msgs = [m for m in messages if isinstance(m, SystemMessage)]

    # Keep last 10 messages (configurable)
    recent_messages = messages[-10:]

    # Messages to summarize
    middle_messages = [m for m in messages if m not in system_msgs and m not in recent_messages]

    if not middle_messages:
        return messages, ""

    # Create summary using LLM
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(model=settings.openai_model, temperature=0)

    summary_prompt = f"""Summarize this conversation history in 2-3 sentences, focusing on:
    - Main topics discussed
    - Key information retrieved
    - User's primary goals

    Conversation:
    {format_messages_for_summary(middle_messages)}
    """

    summary_msg = await llm.ainvoke([HumanMessage(content=summary_prompt)])
    summary = summary_msg.content

    # Reconstruct message list
    trimmed = system_msgs + [
        SystemMessage(content=f"Previous conversation summary: {summary}")
    ] + recent_messages

    return trimmed, summary

def format_messages_for_summary(messages: List[BaseMessage]) -> str:
    """Format messages as readable text for summarization."""
    lines = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            lines.append(f"User: {msg.content}")
        elif isinstance(msg, AIMessage):
            lines.append(f"Assistant: {msg.content}")
    return "\n".join(lines)
```

**Config additions** (`backend/app/core/config.py`):

```python
# Conversation memory settings
max_conversation_tokens: int = Field(
    default=8000,  # Reserve space for system prompt + retrieval context
    description="Max tokens for conversation history"
)
recent_message_count: int = Field(
    default=10,
    description="Number of recent messages to always keep"
)
```

### 1.3 Update Generator to Use Full Context

**File:** `backend/app/agents/nodes/generator.py`

**Enhancement:** Include conversation summary in system prompt

```python
async def generate_answer(state: AgentState) -> Dict[str, Any]:
    # ... existing code ...

    # Build context-aware system prompt
    system_prompt_parts = [
        "You are a helpful AI assistant that answers questions using retrieved documentation."
    ]

    # Add conversation summary if available
    if state.get("conversation_summary"):
        system_prompt_parts.append(
            f"\nPrevious conversation context:\n{state['conversation_summary']}"
        )

    # Add retrieved documents
    if state.get("reranked_documents"):
        docs_text = format_documents(state["reranked_documents"])
        system_prompt_parts.append(
            f"\nRelevant documentation:\n{docs_text}"
        )

    system_prompt = "\n".join(system_prompt_parts)

    # ... rest of generation logic ...
```

---

## Phase 2: Adaptive Query Classification

### 2.1 Query Classifier Node

**File:** `backend/app/agents/nodes/classifier.py` (NEW)

**Purpose:** Classify queries to route to appropriate pipeline path

**Classification Types:**

1. **Simple conversational** (no retrieval needed):
   - Greetings: "hi", "hello", "thanks"
   - Clarifications: "yes", "no", "can you explain more?"
   - Meta questions: "what can you help me with?"

2. **Conversational follow-up** (use context, minimal retrieval):
   - "tell me more about that"
   - "what else?"
   - "can you give an example?"

3. **Complex standalone** (full RAG pipeline):
   - Specific technical questions
   - Questions requiring multiple documents
   - Questions about new topics

**Implementation:**

```python
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from app.agents.state import AgentState
from app.core.config import settings

class QueryClassification(BaseModel):
    """Structured output for query classification."""
    query_type: str = Field(
        description="Type: 'simple', 'conversational_followup', or 'complex_standalone'"
    )
    needs_retrieval: bool = Field(
        description="Whether retrieval is needed"
    )
    reasoning: str = Field(
        description="Brief explanation of classification"
    )

async def classify_query(state: AgentState) -> Dict[str, Any]:
    """
    Classify the user's query to determine routing.

    Uses LLM with structured output for reliable classification.
    """
    query = state["query"]
    messages = state["messages"]

    # Get last few messages for context
    recent_context = messages[-5:] if len(messages) > 5 else messages
    context_str = format_messages_for_classifier(recent_context)

    # Use structured output for reliable classification
    llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=0
    ).with_structured_output(QueryClassification)

    classification_prompt = f"""Classify this user query to determine how to handle it.

Context (recent messages):
{context_str}

Current query: {query}

Classification rules:
1. "simple" - Greetings, thanks, meta questions, very short responses → no retrieval
2. "conversational_followup" - Refers to previous messages ("tell me more", "what about X?") → minimal retrieval
3. "complex_standalone" - Technical questions, new topics, requires documentation → full retrieval

Examples:
- "hi" → simple, no retrieval
- "thanks!" → simple, no retrieval
- "tell me more about that" → conversational_followup, maybe retrieval
- "how do I implement OAuth in FastAPI?" → complex_standalone, needs retrieval
- "what about error handling?" (after discussing FastAPI) → conversational_followup, needs retrieval

Classify the current query."""

    result: QueryClassification = await llm.ainvoke([
        SystemMessage(content="You are a query classification expert."),
        HumanMessage(content=classification_prompt)
    ])

    return {
        "query_type": result.query_type,
        "needs_retrieval": result.needs_retrieval,
        "pipeline_path": "simple" if result.query_type == "simple" else "complex"
    }

def format_messages_for_classifier(messages: List[BaseMessage]) -> str:
    """Format recent messages for classification context."""
    lines = []
    for msg in messages[:-1]:  # Exclude current query
        if isinstance(msg, HumanMessage):
            lines.append(f"User: {msg.content}")
        elif isinstance(msg, AIMessage):
            # Truncate long AI responses
            content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
            lines.append(f"Assistant: {content}")
    return "\n".join(lines) if lines else "No previous context"
```

### 2.2 Update Router for Conditional Routing

**File:** `backend/app/agents/nodes/router.py`

**Enhancement:** Add routing logic based on classification

```python
def route_after_classification(state: AgentState) -> str:
    """
    Route based on query classification.

    Returns:
        - "simple_answer" for simple queries
        - "retrieval" for queries needing RAG pipeline
    """
    query_type = state.get("query_type", "complex_standalone")
    needs_retrieval = state.get("needs_retrieval", True)

    # Simple queries go directly to generator
    if query_type == "simple" or not needs_retrieval:
        return "simple_answer"

    # All other queries go through retrieval
    return "retrieval"
```

### 2.3 Simple Answer Node

**File:** `backend/app/agents/nodes/simple_answer.py` (NEW)

**Purpose:** Handle simple queries without retrieval

```python
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage
from app.agents.state import AgentState
from app.core.config import settings

async def generate_simple_answer(state: AgentState) -> Dict[str, Any]:
    """
    Generate answer for simple queries without retrieval.

    Uses conversation context only.
    """
    messages = state["messages"]

    # Use LLM with conversation context
    llm = ChatOpenAI(model=settings.openai_model, temperature=0.7)

    # Simple system prompt
    system_msg = """You are a helpful AI assistant. Respond naturally to the user.
For greetings, be friendly and brief.
For questions about your capabilities, explain you can answer questions about technical documentation using RAG.
For follow-up questions, use the conversation context to provide helpful responses."""

    # Get response
    response = await llm.ainvoke([
        {"role": "system", "content": system_msg},
        *[{"role": msg.type, "content": msg.content} for msg in messages]
    ])

    return {
        "messages": [AIMessage(content=response.content)],
        "final_answer": response.content
    }
```

---

## Phase 3: Context Window Management

### 3.1 Token Counting Utilities

**File:** `backend/app/utils/token_counter.py` (NEW)

```python
import tiktoken
from typing import List
from langchain_core.messages import BaseMessage

class TokenCounter:
    """Utility for counting tokens in messages and text."""

    def __init__(self, model: str = "gpt-4"):
        self.encoding = tiktoken.encoding_for_model(model)

    def count_message_tokens(self, message: BaseMessage) -> int:
        """Count tokens in a single message."""
        # Count message content
        tokens = len(self.encoding.encode(message.content))

        # Add overhead for message formatting (role, etc.)
        tokens += 4  # Approximate overhead per message

        return tokens

    def count_messages_tokens(self, messages: List[BaseMessage]) -> int:
        """Count total tokens in message list."""
        return sum(self.count_message_tokens(msg) for msg in messages)

    def count_text_tokens(self, text: str) -> int:
        """Count tokens in raw text."""
        return len(self.encoding.encode(text))

    def estimate_context_usage(
        self,
        messages: List[BaseMessage],
        system_prompt: str = "",
        retrieved_docs: str = ""
    ) -> dict:
        """
        Estimate total context window usage.

        Returns:
            {
                "messages": token count,
                "system": token count,
                "documents": token count,
                "total": total tokens,
                "remaining": tokens left (assumes 8k context)
            }
        """
        msg_tokens = self.count_messages_tokens(messages)
        sys_tokens = self.count_text_tokens(system_prompt)
        doc_tokens = self.count_text_tokens(retrieved_docs)

        total = msg_tokens + sys_tokens + doc_tokens

        return {
            "messages": msg_tokens,
            "system": sys_tokens,
            "documents": doc_tokens,
            "total": total,
            "remaining": 8000 - total  # Adjust based on model
        }
```

### 3.2 Message Trimming Strategies

**File:** `backend/app/utils/message_trimmer.py` (NEW)

```python
from typing import List, Tuple
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from app.utils.token_counter import TokenCounter

class MessageTrimmer:
    """Strategies for trimming conversation history."""

    def __init__(self, token_counter: TokenCounter):
        self.counter = token_counter

    def trim_to_token_limit(
        self,
        messages: List[BaseMessage],
        max_tokens: int,
        keep_recent: int = 6  # Keep last 3 exchanges (user + assistant)
    ) -> List[BaseMessage]:
        """
        Trim messages to fit within token limit.

        Strategy:
        1. Always keep system messages
        2. Always keep last N messages (recent context)
        3. Remove oldest messages first
        """
        if self.counter.count_messages_tokens(messages) <= max_tokens:
            return messages

        # Separate message types
        system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
        other_msgs = [m for m in messages if not isinstance(m, SystemMessage)]

        # Keep recent messages
        recent = other_msgs[-keep_recent:]
        older = other_msgs[:-keep_recent]

        # Calculate tokens used by system + recent
        base_tokens = (
            self.counter.count_messages_tokens(system_msgs) +
            self.counter.count_messages_tokens(recent)
        )

        # Add older messages until limit
        remaining_tokens = max_tokens - base_tokens
        trimmed_older = []

        # Add from oldest to newest until we hit limit
        for msg in reversed(older):
            msg_tokens = self.counter.count_message_tokens(msg)
            if msg_tokens <= remaining_tokens:
                trimmed_older.insert(0, msg)
                remaining_tokens -= msg_tokens
            else:
                break

        return system_msgs + trimmed_older + recent

    def create_sliding_window(
        self,
        messages: List[BaseMessage],
        window_size: int = 10
    ) -> List[BaseMessage]:
        """
        Simple sliding window: keep system + last N messages.
        """
        system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
        other_msgs = [m for m in messages if not isinstance(m, SystemMessage)]

        return system_msgs + other_msgs[-window_size:]
```

### 3.3 Conversation Summarization

**File:** `backend/app/utils/conversation_summarizer.py` (NEW)

```python
from typing import List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from app.core.config import settings

class ConversationSummarizer:
    """Create summaries of conversation history."""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0
        )

    async def summarize_messages(
        self,
        messages: List[BaseMessage],
        max_summary_length: int = 500
    ) -> str:
        """
        Summarize a list of messages.

        Returns concise summary focusing on:
        - Topics discussed
        - Key information shared
        - User goals/intent
        """
        if not messages:
            return ""

        # Format messages
        conversation = self._format_for_summary(messages)

        prompt = f"""Summarize this conversation concisely (max {max_summary_length} chars).
Focus on:
1. Main topics discussed
2. Key technical details or solutions provided
3. User's goals or questions

Conversation:
{conversation}

Summary:"""

        response = await self.llm.ainvoke([
            HumanMessage(content=prompt)
        ])

        summary = response.content[:max_summary_length]
        return summary

    def _format_for_summary(self, messages: List[BaseMessage]) -> str:
        """Format messages as text for summarization."""
        lines = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                lines.append(f"User: {msg.content}")
            elif isinstance(msg, AIMessage):
                # Exclude tool calls, keep only text
                content = msg.content if isinstance(msg.content, str) else ""
                if content:
                    lines.append(f"Assistant: {content}")
        return "\n".join(lines)

    async def progressive_summarization(
        self,
        messages: List[BaseMessage],
        chunk_size: int = 20
    ) -> str:
        """
        Summarize long conversations progressively.

        For very long histories (100+ messages):
        1. Split into chunks
        2. Summarize each chunk
        3. Summarize the summaries
        """
        if len(messages) <= chunk_size:
            return await self.summarize_messages(messages)

        # Split into chunks
        chunks = [
            messages[i:i+chunk_size]
            for i in range(0, len(messages), chunk_size)
        ]

        # Summarize each chunk
        chunk_summaries = []
        for chunk in chunks:
            summary = await self.summarize_messages(chunk, max_summary_length=200)
            chunk_summaries.append(summary)

        # Summarize the summaries
        final_prompt = f"""Combine these conversation summaries into one concise summary:

{chr(10).join(f"{i+1}. {s}" for i, s in enumerate(chunk_summaries))}

Final summary:"""

        response = await self.llm.ainvoke([HumanMessage(content=final_prompt)])
        return response.content
```

### 3.4 Enhanced Context Loader with Management

**Update:** `backend/app/agents/nodes/context_loader.py`

```python
from app.utils.token_counter import TokenCounter
from app.utils.message_trimmer import MessageTrimmer
from app.utils.conversation_summarizer import ConversationSummarizer

async def load_conversation_context(state: AgentState) -> Dict[str, Any]:
    """
    Load and manage conversation context with trimming and summarization.
    """
    messages = list(state["messages"])

    # Initialize utilities
    counter = TokenCounter(model=settings.openai_model)
    trimmer = MessageTrimmer(counter)
    summarizer = ConversationSummarizer()

    # Count current tokens
    current_tokens = counter.count_messages_tokens(messages)

    # If under limit, return as-is
    if current_tokens <= settings.max_conversation_tokens:
        return {
            "context_window_tokens": current_tokens,
            "conversation_summary": ""
        }

    # Strategy 1: Try simple trimming first
    trimmed = trimmer.trim_to_token_limit(
        messages,
        max_tokens=settings.max_conversation_tokens,
        keep_recent=settings.recent_message_count
    )

    trimmed_tokens = counter.count_messages_tokens(trimmed)

    # If trimming is enough, use it
    if trimmed_tokens <= settings.max_conversation_tokens:
        return {
            "messages": trimmed,
            "context_window_tokens": trimmed_tokens,
            "conversation_summary": ""
        }

    # Strategy 2: Trim + summarize older messages
    system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
    other_msgs = [m for m in messages if not isinstance(m, SystemMessage)]

    # Keep last N messages
    recent = other_msgs[-settings.recent_message_count:]
    older = other_msgs[:-settings.recent_message_count]

    # Summarize older messages
    if older:
        summary = await summarizer.summarize_messages(older)
        summary_msg = SystemMessage(content=f"Previous conversation summary:\n{summary}")

        reconstructed = system_msgs + [summary_msg] + recent

        return {
            "messages": reconstructed,
            "conversation_summary": summary,
            "context_window_tokens": counter.count_messages_tokens(reconstructed)
        }

    # Fallback: Just use recent messages
    return {
        "messages": system_msgs + recent,
        "context_window_tokens": counter.count_messages_tokens(system_msgs + recent),
        "conversation_summary": "Older messages truncated"
    }
```

---

## Phase 4: Frontend Enhancements

### 4.1 Display Conversation Indicators

**File:** `frontend/components/chat/message-bubble.tsx`

**Enhancement:** Show when message is using conversational context

```typescript
// Add badge for messages using conversation context
{message.metadata?.usedConversationContext && (
  <div className="flex items-center gap-1 text-xs text-muted-foreground mt-2">
    <MessageCircle className="w-3 h-3" />
    <span>Used conversation context</span>
  </div>
)}

// Show if query was classified as simple
{message.metadata?.queryType === 'simple' && (
  <div className="text-xs text-muted-foreground mt-1">
    Quick response
  </div>
)}
```

### 4.2 Context Window Status

**File:** `frontend/components/chat/chat-input.tsx`

**Enhancement:** Show context window usage

```typescript
const ContextStatus = ({ usage }: { usage?: ContextUsage }) => {
  if (!usage) return null;

  const percentage = (usage.total / 8000) * 100;
  const color = percentage > 80 ? 'text-red-500' :
                percentage > 60 ? 'text-yellow-500' :
                'text-green-500';

  return (
    <div className="flex items-center gap-2 text-xs text-muted-foreground">
      <div className={`w-16 h-1.5 bg-gray-200 rounded-full overflow-hidden`}>
        <div
          className={`h-full ${color} bg-current transition-all`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className={color}>
        {usage.total} / 8000 tokens
      </span>
    </div>
  );
};
```

### 4.3 Conversation Summary Display

**File:** `frontend/components/chat/conversation-summary.tsx` (NEW)

```typescript
export function ConversationSummary({ summary }: { summary?: string }) {
  if (!summary) return null;

  return (
    <div className="mb-4 p-3 bg-muted/50 rounded-lg border border-border">
      <div className="flex items-start gap-2">
        <History className="w-4 h-4 mt-0.5 text-muted-foreground" />
        <div className="flex-1">
          <div className="text-xs font-medium text-muted-foreground mb-1">
            Earlier conversation
          </div>
          <p className="text-sm text-muted-foreground">
            {summary}
          </p>
        </div>
      </div>
    </div>
  );
}
```

---

## Phase 5: Testing & Observability

### 5.1 Test Scenarios

**File:** `backend/tests/test_conversational_agent.py` (NEW)

```python
import pytest
from app.agents.graph import create_graph

@pytest.mark.asyncio
async def test_simple_greeting():
    """Test that greetings don't trigger retrieval."""
    graph = create_graph()
    result = await graph.ainvoke({
        "messages": [{"role": "user", "content": "Hello!"}],
        "user_id": "test_user"
    })

    assert result["query_type"] == "simple"
    assert result["needs_retrieval"] is False
    assert "final_answer" in result

@pytest.mark.asyncio
async def test_conversational_followup():
    """Test follow-up questions use context."""
    graph = create_graph()

    # First question
    result1 = await graph.ainvoke({
        "messages": [{"role": "user", "content": "What is FastAPI?"}],
        "user_id": "test_user",
        "session_id": "test_session"
    })

    # Follow-up
    result2 = await graph.ainvoke({
        "messages": [
            {"role": "user", "content": "What is FastAPI?"},
            {"role": "assistant", "content": result1["final_answer"]},
            {"role": "user", "content": "Can you tell me more about its routing?"}
        ],
        "user_id": "test_user",
        "session_id": "test_session"
    })

    assert result2["query_type"] in ["conversational_followup", "complex_standalone"]
    assert "routing" in result2["final_answer"].lower()

@pytest.mark.asyncio
async def test_context_window_trimming():
    """Test message trimming when context is full."""
    graph = create_graph()

    # Create long conversation
    messages = []
    for i in range(50):
        messages.append({"role": "user", "content": f"Question {i}"})
        messages.append({"role": "assistant", "content": f"Answer {i}"})

    messages.append({"role": "user", "content": "Final question"})

    result = await graph.ainvoke({
        "messages": messages,
        "user_id": "test_user",
        "session_id": "test_session"
    })

    # Should have summary or trimmed messages
    assert (
        result.get("conversation_summary") or
        len(result["messages"]) < len(messages)
    )
```

### 5.2 LangSmith Tracing

**File:** `backend/app/core/config.py`

**Enhancement:** Add metadata for conversational features

```python
# In graph execution
async def execute_graph_with_tracing(state: dict, config: dict):
    """Execute graph with enhanced tracing."""

    # Add metadata for LangSmith
    config["metadata"] = {
        **config.get("metadata", {}),
        "query_type": state.get("query_type"),
        "needs_retrieval": state.get("needs_retrieval"),
        "context_tokens": state.get("context_window_tokens"),
        "has_summary": bool(state.get("conversation_summary")),
        "message_count": len(state.get("messages", []))
    }

    return await graph.ainvoke(state, config)
```

### 5.3 Metrics Collection

**File:** `backend/app/utils/metrics.py` (NEW)

```python
from typing import Dict, Any
from collections import defaultdict

class ConversationMetrics:
    """Track conversation agent metrics."""

    def __init__(self):
        self.query_types = defaultdict(int)
        self.retrieval_hits = defaultdict(int)
        self.token_usage = []
        self.response_times = []

    def track_query(self, query_type: str, needs_retrieval: bool):
        """Track query classification."""
        self.query_types[query_type] += 1
        self.retrieval_hits[needs_retrieval] += 1

    def track_tokens(self, token_count: int):
        """Track token usage."""
        self.token_usage.append(token_count)

    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        return {
            "query_type_distribution": dict(self.query_types),
            "retrieval_rate": self.retrieval_hits[True] / sum(self.retrieval_hits.values()),
            "avg_tokens": sum(self.token_usage) / len(self.token_usage) if self.token_usage else 0,
            "max_tokens": max(self.token_usage) if self.token_usage else 0
        }
```

---

## Implementation Timeline

### Week 1: Foundation

- [ ] Update `AgentState` schema with new fields
- [ ] Implement token counting utilities
- [ ] Implement message trimming strategies
- [ ] Add conversation summarizer
- [ ] Update context loader node
- [ ] Write unit tests for utilities

### Week 2: Query Classification

- [ ] Implement query classifier node
- [ ] Add simple answer node
- [ ] Update router with conditional logic
- [ ] Integrate into agent graph
- [ ] Test classification accuracy
- [ ] Add LangSmith tracing

### Week 3: Graph Integration

- [ ] Update graph with new nodes and routing
- [ ] Update generator to use conversation context
- [ ] Implement context window management
- [ ] Add error handling and fallbacks
- [ ] Integration testing
- [ ] Performance testing

### Week 4: Frontend & Polish

- [ ] Add conversation context indicators to UI
- [ ] Implement context window status display
- [ ] Add conversation summary component
- [ ] Update API to pass new metadata
- [ ] End-to-end testing
- [ ] Documentation updates

### Week 5: Observability & Refinement

- [ ] Set up metrics collection
- [ ] Create monitoring dashboard
- [ ] Tune classification prompts
- [ ] Optimize token usage
- [ ] Load testing
- [ ] Production deployment

---

## Appendix: Best Practices Reference

### A. LangChain Memory Patterns

**Sources:** LangChain Docs - Memory, Conversation Management

1. **Message History**: Use `add_messages` reducer in state
2. **Checkpointing**: PostgresCheckpointer for persistence ✅ (already implemented)
3. **Trimming**: Keep recent N messages + summarize older ones
4. **Context Injection**: Add summaries as SystemMessage

### B. Context Window Strategies

**Sources:** LangChain Docs - Context Management, Token Limits

1. **Token Counting**: Use tiktoken for accurate counts
2. **Sliding Window**: Keep last N messages
3. **Summarization**: LLM-based progressive summarization
4. **Hybrid**: Trim + summarize for optimal balance

### C. Query Classification

**Sources:** LangGraph Docs - Conditional Routing, Workflows

1. **Structured Output**: Use Pydantic models for reliable classification
2. **Context-Aware**: Include recent messages in classification
3. **Fast Path**: Skip retrieval for simple queries
4. **Routing**: Use conditional edges based on classification

### D. Adaptive RAG

**Sources:** LangChain RAG Tutorial, Multi-Agent Workflows

1. **2-Step RAG**: Fast path for simple queries (single LLM call)
2. **Agentic RAG**: Full pipeline for complex queries (tool-based)
3. **Hybrid**: Classify first, then route to appropriate path

---

## Success Metrics

### Technical Metrics

- **Response Time**:
  - Simple queries: < 500ms
  - Complex queries: < 3s
- **Token Efficiency**:
  - Context usage < 8000 tokens
  - Avg. context: 3000-4000 tokens
- **Classification Accuracy**:
  - > 90% correct routing
  - < 5% false negatives (missed retrieval needs)

### User Experience Metrics

- **Conversation Quality**:
  - Maintains context across 10+ turns
  - Correctly references previous messages
  - Handles follow-ups naturally
- **Performance**:
  - No context window errors
  - Graceful degradation when limits hit
  - Smooth streaming experience

---

## References

1. LangChain Conversation Memory: https://docs.langchain.com/oss/python/langchain/conversation-memory
2. LangGraph State Management: https://docs.langchain.com/oss/python/langgraph/thinking-in-langgraph
3. Conditional Routing: https://docs.langchain.com/oss/python/langgraph/graph-api#conditional-edges
4. RAG Best Practices: https://docs.langchain.com/oss/python/langchain/rag
5. Token Management: https://github.com/openai/tiktoken

---

**End of Plan**

Next steps: Get approval, then implement phase-by-phase with iterative testing.
