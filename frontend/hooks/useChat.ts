/**
 * Custom chat hook
 * Handles message sending and SSE streaming with retry and cancellation
 * 
 * @param threadId - Optional thread ID to use for this chat session (from URL params)
 */

'use client'

import { useCallback, useRef, useEffect } from 'react'
import { toast } from 'sonner'
import { useChatStore } from '@/stores/chat-store'
import { useRateLimitStore } from '@/stores/rate-limit-store'
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

/**
 * Generate a title from the user's message (first 50 chars)
 */
function generateTitleFromMessage(message: string): string {
  const cleaned = message.trim()
  if (cleaned.length <= 50) {
    return cleaned
  }
  return cleaned.slice(0, 47) + '...'
}

export function useChat(threadId?: string) {
  const {
    messages,
    isLoading,
    error,
    currentAgent,
    agentHistory,
    streamingMetrics,
    currentThreadId,
    addUserMessage,
    startStreamingMessage,
    appendToStreamingMessage,
    addCitationToStreamingMessage,
    finishStreamingMessage,
    setCurrentAgent,
    startAgent,
    completeAgent,
    errorAgent,
    resetAgentHistory,
    setQualityScore,
    resetStreamingMetrics,
    setLoading,
    setError,
    clearMessages,
    setCurrentThreadId,
    loadThreads,
    updateThreadTitle,
  } = useChatStore()

  const { setRateLimit } = useRateLimitStore()

  // AbortController for cancellation
  const abortControllerRef = useRef<AbortController | null>(null)
  const sseClientRef = useRef<SSEClient | null>(null)

  // Sync the thread ID from URL params to store
  useEffect(() => {
    if (threadId && threadId !== currentThreadId) {
      console.log(`[useChat] Syncing threadId from URL: ${threadId}`)
      setCurrentThreadId(threadId)
    }
  }, [threadId, currentThreadId, setCurrentThreadId])

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || isLoading) return

      try {
        // Track if this is the first message in the thread (for auto-title generation)
        const isFirstMessage = messages.length === 0
        
        // Add user message to UI immediately
        addUserMessage(content)
        setLoading(true)
        setError(null)
        
        // Reset agent history and streaming metrics for new conversation turn
        resetAgentHistory()
        resetStreamingMetrics()

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
          body: { 
            message: content,
            stream: true,
            thread_id: currentThreadId || null  // null = new thread, UUID = existing thread
          },
          maxRetries: 3,
          baseDelay: 1000,
          maxDelay: 10000,
          signal: abortControllerRef.current.signal,
          onHeaders: (headers) => {
            // Parse and store rate limit headers
            const limit = headers.get('X-RateLimit-Limit')
            const remaining = headers.get('X-RateLimit-Remaining')
            const reset = headers.get('X-RateLimit-Reset')

            console.log('[Rate Limit] Headers received:', {
              limit,
              remaining,
              reset,
              resetDate: reset ? new Date(parseInt(reset) * 1000).toLocaleString() : null
            })

            if (limit && remaining && reset) {
              const limitNum = parseInt(limit)
              const remainingNum = parseInt(remaining)
              const resetNum = parseInt(reset)
              
              // Skip if rate limiting is disabled (limit=0)
              if (limitNum === 0) {
                console.log('[Rate Limit] Rate limiting disabled (limit=0), skipping')
                return
              }
              
              console.log('[Rate Limit] Updating store:', {
                limit: limitNum,
                remaining: remainingNum,
                reset: resetNum,
                isRateLimited: remainingNum === 0
              })
              
              setRateLimit(limitNum, remainingNum, resetNum)
            } else {
              console.log('[Rate Limit] Missing headers, not updating store')
            }
          },
          onEvent: (event) => {
            // Parse and handle event
            switch (event.event) {
              case 'agent_start': {
                const data = parseEventData<AgentStartEvent>(event)
                if (data) {
                  console.log('[SSE] Agent started:', data.agent)
                  // Use new startAgent method to track in history
                  startAgent(data.agent)
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
                  console.log('[Citation Event]', data) // DEBUG
                  
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
                  const citation = {
                    document_id: data.chunk_id || 'unknown',
                    document_title: data.document_title || 'Unknown Document',
                    chunk_id: data.chunk_id,
                    content: data.preview || data.content || '',
                    similarity_score: data.score ?? data.similarity_score,
                    original_score: data.original_score,  // Original cosine similarity
                  }
                  console.log('[Adding Citation]', citation) // DEBUG
                  addCitationToStreamingMessage(citation)
                }
                break
              }

              case 'agent_complete': {
                const data = parseEventData<AgentCompleteEvent>(event)
                if (data) {
                  console.log('[SSE] Agent completed:', data.agent)
                  // Mark agent as complete in history (keeps it visible)
                  completeAgent(data.agent)
                }
                break
              }

              case 'agent_error': {
                const data = parseEventData<AgentErrorEvent>(event)
                if (data) {
                  console.error('[SSE] Agent error:', data.error)
                  // Mark agent as error in history
                  errorAgent(data.agent)
                  toast.error(`Agent error: ${data.error}`)
                }
                break
              }

              case 'validation': {
                const data = parseEventData<ValidationEvent>(event)
                if (data) {
                  console.log('[SSE] Validation:', data.passed ? 'PASSED' : 'FAILED', `(score: ${data.score})`)
                  // Store quality score in metrics
                  setQualityScore(data.score)
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
                  console.log('[Thread] Current thread ID:', currentThreadId)
                  console.log('[Thread] Response thread ID:', data.thread_id)
                  
                  // Capture thread_id for multi-turn conversations
                  if (data.thread_id) {
                    if (!currentThreadId) {
                      console.log('[Thread] NEW THREAD created:', data.thread_id)
                      setCurrentThreadId(data.thread_id)
                      
                      // Refresh thread list to show new conversation
                      console.log('[Thread] Refreshing thread list...')
                      loadThreads().then(() => {
                        console.log('[Thread] Thread list refreshed successfully')
                      }).catch(err => {
                        console.error('[Thread] Failed to refresh thread list:', err)
                      })
                    } else if (currentThreadId !== data.thread_id) {
                      console.warn('[Thread] Thread ID mismatch!', {
                        current: currentThreadId,
                        response: data.thread_id
                      })
                      setCurrentThreadId(data.thread_id)
                    } else {
                      console.log('[Thread] Continuing existing thread:', data.thread_id)
                    }
                    
                    // Update thread title if this was the first message
                    if (isFirstMessage && data.thread_id) {
                      const newTitle = generateTitleFromMessage(content)
                      console.log('[Thread] Updating title for first message:', newTitle)
                      updateThreadTitle(data.thread_id, newTitle)
                        .then(() => {
                          console.log('[Thread] Title updated successfully')
                        })
                        .catch(err => {
                          console.error('[Thread] Failed to update title:', err)
                        })
                    }
                  }
                  
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
      messages.length,
      isLoading,
      currentThreadId,
      addUserMessage,
      startStreamingMessage,
      appendToStreamingMessage,
      addCitationToStreamingMessage,
      finishStreamingMessage,
      setCurrentAgent,
      startAgent,
      completeAgent,
      errorAgent,
      resetAgentHistory,
      setQualityScore,
      resetStreamingMetrics,
      setLoading,
      setError,
      setRateLimit,
      setCurrentThreadId,
      loadThreads,
      updateThreadTitle,
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
    agentHistory,
    streamingMetrics,
    sendMessage,
    cancelStream,
    clearMessages,
  }
}
