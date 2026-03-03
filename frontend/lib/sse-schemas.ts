/**
 * Zod schemas for all SSE event payloads.
 *
 * These mirror the backend Pydantic event models so that every payload received
 * over the SSE stream is validated at runtime before being consumed by the UI.
 * Unknown or malformed events are logged and discarded rather than causing
 * runtime type errors higher up the call stack.
 */

import { z } from 'zod'

// ---------------------------------------------------------------------------
// Individual event schemas
// ---------------------------------------------------------------------------

export const TokenEventSchema = z.object({
  token: z.string(),
  model: z.string().optional(),
})

export const CitationEventSchema = z.object({
  chunk_id: z.string(),
  document_title: z.string(),
  content: z.string().optional(),
  preview: z.string().optional(),
  similarity_score: z.number().optional(),
  /** RRF-fused score sent as "score" by the backend */
  score: z.number().optional(),
  original_score: z.number().optional(),
  source: z.string().optional(),
})

export const AgentStartEventSchema = z.object({
  agent: z.string(),
  message: z.string().optional(),
  timestamp: z.string().optional(),
})

export const AgentCompleteEventSchema = z.object({
  agent: z.string(),
  result: z.record(z.string(), z.unknown()).optional(),
  timestamp: z.string().optional(),
})

export const AgentErrorEventSchema = z.object({
  agent: z.string(),
  error: z.string(),
  timestamp: z.string().optional(),
})

export const ValidationEventSchema = z.object({
  passed: z.boolean(),
  score: z.number(),
  issues: z.array(z.string()),
})

export const ThreadCreatedEventSchema = z.object({
  thread_id: z.string(),
})

export const EndEventSchema = z.object({
  thread_id: z.string(),
  success: z.boolean(),
  error: z.string().optional(),
})

export const ErrorEventSchema = z.object({
  error: z.string(),
  details: z.string().optional(),
})

export const QueryClassificationEventSchema = z.object({
  query_type: z.string(),
  needs_retrieval: z.boolean(),
  reasoning: z.string(),
  pipeline_path: z.string(),
})

export const ContextStatusEventSchema = z.object({
  total_tokens: z.number(),
  max_tokens: z.number(),
  remaining_tokens: z.number(),
  message_count: z.number(),
  percentage_used: z.number(),
})

export const ConversationSummaryEventSchema = z.object({
  summary: z.string(),
  messages_summarized: z.number(),
  messages_kept: z.number(),
})

// ---------------------------------------------------------------------------
// Registry — maps SSE event name → schema
// ---------------------------------------------------------------------------

export const eventSchemas = {
  token: TokenEventSchema,
  citation: CitationEventSchema,
  agent_start: AgentStartEventSchema,
  agent_complete: AgentCompleteEventSchema,
  agent_error: AgentErrorEventSchema,
  validation: ValidationEventSchema,
  thread_created: ThreadCreatedEventSchema,
  end: EndEventSchema,
  error: ErrorEventSchema,
  query_classification: QueryClassificationEventSchema,
  context_status: ContextStatusEventSchema,
  conversation_summary: ConversationSummaryEventSchema,
} as const

export type EventSchemas = typeof eventSchemas
export type SSEEventName = keyof EventSchemas
