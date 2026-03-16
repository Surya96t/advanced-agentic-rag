/**
 * Chat message types for Advanced Agentic RAG
 */

/**
 * Citation from source document (matches backend SearchResult)
 */
export interface Citation {
  document_id: string
  document_title: string
  chunk_id: string
  content: string
  similarity_score?: number  // RRF score (0-1, lower is better for ranking)
  original_score?: number    // Original cosine similarity (0-1, higher is better for display)
  chunk_index?: number
}

/**
 * Inline citation marker source — maps [N] in the LLM response to its source.
 * Matches the CitationMarkerSchema in sse-schemas.ts.
 */
export interface CitationMarker {
  chunk_id: string
  document_id?: string
  document_title: string
  content?: string
  score?: number
  source?: string
}

/**
 * Chat message
 */
export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  /** Marker number (string key) → source info for inline [N] citations in the response. */
  citationMap?: Record<string, CitationMarker>
  timestamp: Date
  lowConfidence?: boolean
  metadata?: {
    usedConversationContext?: boolean
    queryType?: 'simple' | 'conversational_followup' | 'complex_standalone'
    needsRetrieval?: boolean
    pipelinePath?: 'simple' | 'complex'
  }
}

/**
 * Backend chat response (non-streaming)
 * Matches FastAPI ChatResponse schema
 */
export interface ChatResponse {
  thread_id?: string
  content: string  // Backend uses 'content', not 'response'
  sources: Citation[]  // Backend uses 'sources', not 'citations'
  quality_score?: number
  metadata?: {
    model?: string
    tokens_used?: number
    processing_time?: number
  }
}

/**
 * Chat request payload
 */
export interface ChatRequest {
  message: string
  thread_id?: string
  source_ids?: string[]
  stream?: boolean
  max_retries?: number
}

/**
 * Streaming event types (match backend schemas)
 */

export interface StartEvent {
  thread_id: string
  message: string
  timestamp: string
}

export interface TokenEvent {
  token: string
}

export interface CitationEvent {
  chunk_id: string
  document_title: string
  content?: string
  preview?: string
  similarity_score?: number
  score?: number  // Backend sends 'score' (RRF), not 'similarity_score'
  original_score?: number  // Original cosine similarity for display
  source?: string  // Search method (vector/text/hybrid/reranked)
}

export interface AgentStartEvent {
  agent: string
  timestamp: string
}

export interface AgentCompleteEvent {
  agent: string
  timestamp: string
}

export interface AgentErrorEvent {
  agent: string
  error: string
  timestamp: string
}

export interface EndEvent {
  thread_id: string
  success: boolean
  error?: string
}

export interface ThreadCreatedEvent {
  thread_id: string
}

export interface ValidationEvent {
  passed: boolean
  score: number
  issues: string[]
}

export interface ErrorEvent {
  error: string
  details?: string
}

/**
 * Union type for all streaming events
 */
export type StreamEvent =
  | { type: 'start'; data: StartEvent }
  | { type: 'token'; data: TokenEvent }
  | { type: 'citation'; data: CitationEvent }
  | { type: 'agent_start'; data: AgentStartEvent }
  | { type: 'agent_complete'; data: AgentCompleteEvent }
  | { type: 'agent_error'; data: AgentErrorEvent }
  | { type: 'validation'; data: ValidationEvent }
  | { type: 'thread_created'; data: ThreadCreatedEvent }
  | { type: 'end'; data: EndEvent }
  | { type: 'error'; data: ErrorEvent }
