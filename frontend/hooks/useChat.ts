/**
 * Custom chat hook
 * Handles message sending and SSE streaming with retry and cancellation
 */

'use client'

import { useCallback, useRef } from 'react'
import { toast } from 'sonner'
import { useChatStore } from '@/stores/chat-store'
import { SSEClient } from '@/lib/sse-client'
import { parseEventData } from '@/lib/sse-parser'
import { sanitizeToken, isCitationSafe } from '@/lib/sanitizer'
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

  // AbortController for cancellation
  const abortControllerRef = useRef<AbortController | null>(null)
  const sseClientRef = useRef<SSEClient | null>(null)

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || isLoading) return

      try {
        // Add user message to UI immediately
        addUserMessage(content)
        setLoading(true)
        setError(null)

        // Create AbortController for cancellation
        abortControllerRef.current = new AbortController()

        // Track streaming state
        let messageStarted = false

        // Create SSE client with retry logic
        const client = new SSEClient({
          url: '/api/chat',
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: { message: content },
          maxRetries: 3,
          baseDelay: 1000,
          maxDelay: 10000,
          signal: abortControllerRef.current.signal,
          onEvent: (event) => {
            // Parse and handle event
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
                  // Sanitize token before display
                  const sanitizedToken = sanitizeToken(data.token)
                  
                  // Ensure message is started
                  if (!messageStarted) {
                    startStreamingMessage()
                    messageStarted = true
                  }
                  appendToStreamingMessage(sanitizedToken)
                }
                break
              }

              case 'citation': {
                const data = parseEventData<CitationEvent>(event)
                if (data) {
                  // Validate citation content
                  if (!isCitationSafe(data)) {
                    console.warn('[Security] Blocked unsafe citation')
                    return
                  }

                  // Ensure message is started
                  if (!messageStarted) {
                    startStreamingMessage()
                    messageStarted = true
                  }
                  // Convert CitationEvent to Citation format
                  addCitationToStreamingMessage({
                    document_id: data.chunk_id?.split('_')[0] || 'unknown',
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
                  // Ensure message is started
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
          onError: (error, retryCount) => {
            console.error(`[SSE] Connection error (attempt ${retryCount}):`, error.message)
            if (retryCount === 1) {
              toast.error('Connection lost, retrying...')
            }
          },
          onReconnect: (retryCount) => {
            console.log(`[SSE] Reconnecting (attempt ${retryCount})...`)
            toast.info('Reconnecting...')
          },
        })

        sseClientRef.current = client

        // Connect and stream
        await client.connect()

        // Log metrics
        const metrics = client.getMetrics()
        console.log('[SSE] Stream metrics:', metrics)

      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to send message'
        
        // Don't show error toast for user cancellation
        if (!errorMessage.includes('cancelled') && !errorMessage.includes('aborted')) {
          setError(errorMessage)
          toast.error(errorMessage)
        }
        
        finishStreamingMessage()
      } finally {
        setLoading(false)
        setCurrentAgent(null)
        abortControllerRef.current = null
        sseClientRef.current = null
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

  /**
   * Cancel current streaming request
   */
  const cancelStream = useCallback(() => {
    if (abortControllerRef.current) {
      console.log('[SSE] Cancelling stream')
      abortControllerRef.current.abort()
      sseClientRef.current?.cancel()
      toast.info('Generation cancelled')
      finishStreamingMessage()
      setLoading(false)
      setCurrentAgent(null)
    }
  }, [finishStreamingMessage, setLoading, setCurrentAgent])

  return {
    messages,
    isLoading,
    error,
    currentAgent,
    sendMessage,
    cancelStream,
    clearMessages,
  }
}
