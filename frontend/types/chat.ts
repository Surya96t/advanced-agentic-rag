/**
 * Chat message types for Integration Forge
 */

/**
 * Citation from source document (matches backend SearchResult)
 */
export interface Citation {
  document_id: string
  document_title: string
  chunk_id: string
  content: string
  similarity_score?: number
  chunk_index?: number
}

/**
 * Chat message
 */
export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  timestamp: Date
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
  content: string
  preview: string
  similarity_score?: number
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
  | { type: 'citation'; data: CitationEvent }
  | { type: 'agent_start'; data: AgentStartEvent }
  | { type: 'agent_complete'; data: AgentCompleteEvent }
  | { type: 'agent_error'; data: AgentErrorEvent }
  | { type: 'validation'; data: ValidationEvent }
  | { type: 'end'; data: EndEvent }
  | { type: 'error'; data: ErrorEvent }
