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

/** Emitted when the validator retries — the frontend should clear its streaming buffer. */
export const TokenResetEventSchema = z.object({
  reason: z.string().optional(),
})

export const CitationEventSchema = z.object({
  chunk_id: z.string(),
  document_id: z.string().optional(),
  document_title: z.string(),
  content: z.string().nullish(),
  preview: z.string().nullish(),       // backend sends null when no preview — must use nullish()
  similarity_score: z.number().nullish(),
  /** RRF-fused score sent as "score" by the backend */
  score: z.number().optional(),
  original_score: z.number().nullish(), // backend sends null when no original score — must use nullish()
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
  done: z.boolean().optional(),
  total_time_ms: z.number().nullish(),
  token_count: z.number().nullish(),
  thread_id: z.string().nullish(),
  success: z.boolean(),
  error: z.string().nullish(),
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

export const ThreadTitleEventSchema = z.object({
  title: z.string(),
  thread_id: z.string(),
  timestamp: z.string().optional(),
})

/** Emitted after generator completes with a mapping from inline [N] marker to source. */
export const CitationMarkerSchema = z.object({
  chunk_id: z.string(),
  document_id: z.string().optional(),
  document_title: z.string(),
  content: z.string().optional(),
  score: z.number().optional(),
  source: z.string().optional(),
})

export const CitationMapEventSchema = z.object({
  /** Keys are string marker numbers ("1", "2", ...) matching inline [N] in the response. */
  markers: z.record(z.string(), CitationMarkerSchema),
})

export type CitationMarker = z.infer<typeof CitationMarkerSchema>

// ---------------------------------------------------------------------------
// Registry — maps SSE event name → schema
// ---------------------------------------------------------------------------

export const eventSchemas = {
  token: TokenEventSchema,
  token_reset: TokenResetEventSchema,
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
  thread_title: ThreadTitleEventSchema,
  citation_map: CitationMapEventSchema,
} as const

export type EventSchemas = typeof eventSchemas
export type SSEEventName = keyof EventSchemas
