/**
 * Custom chat hook
 * Handles message sending and SSE streaming
 */

'use client'

import { useCallback } from 'react'
import { toast } from 'sonner'
import { useChatStore } from '@/stores/chat-store'
import { parseSSEStream, parseEventData } from '@/lib/sse-parser'
import type {
  TokenEvent,
  CitationEvent,
  AgentStartEvent,
  AgentCompleteEvent,
  AgentErrorEvent,
  ValidationEvent,
  EndEvent,
  ErrorEvent,
} from '@/types/chat'

export function useChat() {
  const {
    messages,
    isLoading,
    error,
    currentAgent,
    addUserMessage,
    startStreamingMessage,
    appendToStreamingMessage,
    addCitationToStreamingMessage,
    finishStreamingMessage,
    setCurrentAgent,
    setLoading,
    setError,
    clearMessages,
  } = useChatStore()

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || isLoading) return

      try {
        // Add user message to UI immediately
        addUserMessage(content)
        setLoading(true)
        setError(null)

        // Call BFF chat endpoint (streaming)
        const response = await fetch('/api/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            message: content,
          }),
        })

        if (!response.ok) {
          const errorData = await response.json()
          throw new Error(errorData.error || 'Failed to send message')
        }

        // Check if response is streaming
        const contentType = response.headers.get('content-type')
        if (!contentType?.includes('text/event-stream')) {
          // Non-streaming response (fallback)
          const data = await response.json()
          if (data.content) {
            startStreamingMessage()
            appendToStreamingMessage(data.content)
            if (data.sources) {
              data.sources.forEach((source: CitationEvent) => {
                // Convert to Citation format
                addCitationToStreamingMessage({
                  document_id: source.chunk_id.split('_')[0] || 'unknown',
                  document_title: source.document_title,
                  chunk_id: source.chunk_id,
                  content: source.content,
                  similarity_score: source.similarity_score,
                })
              })
            }
            finishStreamingMessage()
          }
          return
        }

        // Start streaming message in UI
        let messageStarted = false

        // Parse SSE stream
        await parseSSEStream(
          response,
          (event) => {
            // Parse event data
            switch (event.event) {
              case 'agent_start': {
                const data = parseEventData<AgentStartEvent>(event)
                if (data) {
                  console.log('[SSE] Agent started:', data.agent)
                  setCurrentAgent(data.agent)
                  // Start streaming message on first agent
                  if (!messageStarted) {
                    startStreamingMessage()
                    messageStarted = true
                  }
                }
                break
              }

              case 'token': {
                const data = parseEventData<TokenEvent>(event)
                if (data) {
                  // Ensure message is started
                  if (!messageStarted) {
                    startStreamingMessage()
                    messageStarted = true
                  }
                  appendToStreamingMessage(data.token)
                }
                break
              }

              case 'citation': {
                const data = parseEventData<CitationEvent>(event)
                if (data) {
                  // Ensure message is started
                  if (!messageStarted) {
                    startStreamingMessage()
                    messageStarted = true
                  }
                  // Convert CitationEvent to Citation format
                  addCitationToStreamingMessage({
                    document_id: data.chunk_id.split('_')[0] || 'unknown',
                    document_title: data.document_title,
                    chunk_id: data.chunk_id,
                    content: data.preview || '',
                    similarity_score: data.similarity_score,
                  })
                }
                break
              }

              case 'agent_complete': {
                const data = parseEventData<AgentCompleteEvent>(event)
                if (data) {
                  console.log('[SSE] Agent completed:', data.agent)
                  setCurrentAgent(null)
                }
                break
              }

              case 'agent_error': {
                const data = parseEventData<AgentErrorEvent>(event)
                if (data) {
                  console.error('[SSE] Agent error:', data.error)
                  toast.error(`Agent error: ${data.error}`)
                }
                break
              }

              case 'validation': {
                const data = parseEventData<ValidationEvent>(event)
                if (data) {
                  console.log('[SSE] Validation:', data.passed ? 'PASSED' : 'FAILED', `(score: ${data.score})`)
                  if (!data.passed && data.issues.length > 0) {
                    console.warn('[SSE] Validation issues:', data.issues)
                  }
                }
                break
              }

              case 'end': {
                const data = parseEventData<EndEvent>(event)
                if (data) {
                  console.log('[SSE] Chat complete:', data.success ? 'success' : 'failed')
                  // Ensure message is started (in case no agents ran)
                  if (!messageStarted) {
                    startStreamingMessage()
                    messageStarted = true
                  }
                  finishStreamingMessage()
                  setCurrentAgent(null)
                  
                  if (!data.success && data.error) {
                    toast.error(`Chat failed: ${data.error}`)
                  }
                }
                break
              }

              case 'error': {
                const data = parseEventData<ErrorEvent>(event)
                if (data) {
                  console.error('[SSE] Error:', data.error)
                  throw new Error(data.error)
                }
                break
              }

              default:
                console.log('[SSE] Unknown event:', event.event)
            }
          },
          (error) => {
            console.error('[SSE] Stream error:', error)
            throw error
          }
        )
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to send message'
        setError(errorMessage)
        toast.error(errorMessage)
        finishStreamingMessage()
      } finally {
        setLoading(false)
        setCurrentAgent(null)
      }
    },
    [
      isLoading,
      addUserMessage,
      startStreamingMessage,
      appendToStreamingMessage,
      addCitationToStreamingMessage,
      finishStreamingMessage,
      setCurrentAgent,
      setLoading,
      setError,
    ]
  )

  return {
    messages,
    isLoading,
    error,
    currentAgent,
    sendMessage,
    clearMessages,
  }
}
