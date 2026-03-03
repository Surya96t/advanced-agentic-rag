/**
 * Custom chat hook
 * Handles message sending and SSE streaming with retry and cancellation
 * 
 * @param threadId - Optional thread ID to use for this chat session (from URL params)
 */

'use client'

import { useCallback, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { useChatStore } from '@/stores/chat-store'
import { useRateLimitStore } from '@/stores/rate-limit-store'
import { SSEClient } from '@/lib/sse-client'
import { parseSSEEvent } from '@/lib/sse-parser'
import { sanitizeToken, isCitationSafe } from '@/lib/sanitizer'
import { revalidateThreads } from '@/app/actions'

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
  const router = useRouter()
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
  // When threadId is present: sync it to store
  // When threadId is undefined (navigating to /chat): clear store to start new chat
  useEffect(() => {
    // CRITICAL: We normally rely on loadThread() to set the thread ID and messages together
    // to avoid a state where ID is set but messages are stale.
    // However, for new chats (threadId=undefined), we must clear the state explicitly.
    
    if (threadId === undefined && currentThreadId !== null) {
      // Only clear if we are NOT in the middle of a redirect or new thread creation
      // We check if messages are empty to verify it's truly a "new" chat state
      // If messages exist, we might have just created a thread and are waiting for redirect
      if (messages.length === 0) {
        console.log('[useChat] Clearing threadId for new chat')
        setCurrentThreadId(null)
      }
    }
  }, [threadId, currentThreadId, setCurrentThreadId, messages.length])

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
                const data = parseSSEEvent('agent_start', event)
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
                const data = parseSSEEvent('token', event)
                if (data) {
                  // Ensure generator is marked as active when we receive tokens
                  // This fixes the issue where UI might get stuck showing 'retriever'
                  // We access store directly to get current state without hook dependency cycle
                  const state = useChatStore.getState()
                  const currentAgentState = state.currentAgent
                  
                  if (currentAgentState !== 'generator') {
                    console.log('[SSE] Token received, forcing active agent to: generator')
                    setCurrentAgent('generator')
                    
                    // Also ensure generator is in the history with start time
                    const history = state.agentHistory
                    const generatorExists = history.some(a => a.name === 'generator')
                    
                    if (!generatorExists) {
                      startAgent('generator')
                    }
                  }

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
                const data = parseSSEEvent('citation', event)
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
                const data = parseSSEEvent('agent_complete', event)
                if (data) {
                  console.log('[SSE] Agent completed:', data.agent)
                  // Mark agent as complete in history (keeps it visible)
                  completeAgent(data.agent)
                }
                break
              }

              case 'agent_error': {
                const data = parseSSEEvent('agent_error', event)
                if (data) {
                  console.error('[SSE] Agent error:', data.error)
                  // Mark agent as error in history
                  errorAgent(data.agent)
                  toast.error(`Agent error: ${data.error}`)
                }
                break
              }

              case 'validation': {
                const data = parseSSEEvent('validation', event)
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

              case 'thread_created': {
                // Handle lazy thread creation - backend sends this event when creating a new thread
                const data = parseSSEEvent('thread_created', event)
                if (data && data.thread_id) {
                  console.log('[SSE] Thread created event received:', data.thread_id)
                  setCurrentThreadId(data.thread_id)
                  
                  // Redirect to the new thread URL
                  console.log('[SSE] Redirecting to /chat/' + data.thread_id)
                  router.push(`/chat/${data.thread_id}`)
                  
                  // Invalidate cache for threads list (will auto-reload on next access)
                  revalidateThreads()
                    .then(() => {
                      console.log('[Thread] Thread cache invalidated')
                      // Trigger a background reload
                      loadThreads()
                    })
                    .catch(err => {
                      console.error('[Thread] Failed to invalidate thread cache:', err)
                    })
                } else {
                  console.error('[SSE] Invalid thread_created event data:', event.data)
                }
                break
              }

              case 'end': {
                const data = parseSSEEvent('end', event)
                if (data) {
                  console.log('[SSE] Chat complete:', data.success ? 'success' : 'failed')
                  console.log('[Thread] Current thread ID:', currentThreadId)
                  console.log('[Thread] Response thread ID:', data.thread_id)
                  
                  // Capture thread_id for multi-turn conversations
                  if (data.thread_id) {
                    if (!currentThreadId) {
                      console.log('[Thread] NEW THREAD created:', data.thread_id)
                      setCurrentThreadId(data.thread_id)
                    } else if (currentThreadId !== data.thread_id) {
                      console.warn('[Thread] Thread ID mismatch!', {
                        current: currentThreadId,
                        response: data.thread_id
                      })
                    } else {
                      console.log('[Thread] Continuing existing thread:', data.thread_id)
                    }

                    // Handle Title Update (First Message) vs Regular Refresh
                    // We avoid firing both to prevent race conditions where we fetch "New Chat" 
                    // before the title update completes.
                    
                    if (isFirstMessage && data.thread_id) {
                      const newTitle = generateTitleFromMessage(content)
                      console.log('[Thread] First message detected. Updating title to:', newTitle)
                      
                      // This will trigger its own refresh after update completes
                      updateThreadTitle(data.thread_id, newTitle)
                        .then(() => {
                          console.log('[Thread] Title updated and list refreshed')
                        })
                        .catch(err => {
                          console.error('[Thread] Failed to update title:', err)
                          // Fallback refresh if title update fails
                          revalidateThreads().then(() => loadThreads())
                        })
                    } else {
                      // Not first message - just refresh to show updated message count/preview
                      console.log('[Thread] Stream ended - refreshing thread list...')
                      revalidateThreads()
                        .then(() => {
                          console.log('[Thread] Thread cache invalidated')
                          loadThreads() // Silent reload (no spinner)
                        })
                        .catch(err => {
                          console.error('[Thread] Failed to refresh thread list:', err)
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
                const data = parseSSEEvent('error', event)
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
      router,
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
