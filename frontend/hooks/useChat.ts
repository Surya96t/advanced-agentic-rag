/**
 * Custom chat hook
 * Handles message sending and SSE streaming with retry and cancellation
 * 
 * @param threadId - Optional thread ID to use for this chat session (from URL params)
 */

'use client'

import { useCallback, useRef, useEffect } from 'react'
import { useUser } from '@clerk/nextjs'
import { toast } from 'sonner'
import { useChatStore } from '@/stores/chat-store'
import { useRateLimitStore } from '@/stores/rate-limit-store'
import { SSEClient } from '@/lib/sse-client'
import { parseSSEEvent } from '@/lib/sse-parser'
import { sanitizeToken, isCitationSafe } from '@/lib/sanitizer'
import { mutateThreadHistory, updateThreadTitleOptimistically, insertThreadOptimistically } from '@/hooks/useThreadHistory'

export function useChat(threadId?: string) {
  const { user } = useUser()
  const {
    messages,
    isLoading,
    error,
    currentAgent,
    agentHistory,
    streamingMetrics,
    thinkingStatus,
    currentThreadId,
    addUserMessage,
    startStreamingMessage,
    appendToStreamingMessage,
    resetStreamingMessage,
    addCitationToStreamingMessage,
    setCitationMapForMessage,
    finishStreamingMessage,
    setCurrentAgent,
    startAgent,
    completeAgent,
    errorAgent,
    resetAgentHistory,
    setQualityScore,
    resetStreamingMetrics,
    setThinkingStatus,
    setLoading,
    setError,
    clearMessages,
    setCurrentThreadId,
  } = useChatStore()

  const { setRateLimit } = useRateLimitStore()

  // AbortController for cancellation
  const abortControllerRef = useRef<AbortController | null>(null)
  const sseClientRef = useRef<SSEClient | null>(null)
  // Token counter for streaming metrics (reset per message)
  const tokenCountRef = useRef(0)

  // ── SSE event logger ────────────────────────────────────────────────────────
  // Logs every SSE event to the browser console w/ a consistent prefix so you
  // can filter by "[SSE]" in DevTools.  Colors distinguish event categories:
  //   🟢 lifecycle (agent_start / end)   🔵 content (token / citation)
  //   🟡 status (thinking / validation)  🔴 errors
  const logSSE = (event: string, data: unknown) => {
    const COLORS: Record<string, string> = {
      token:          'color:#4ade80',   // green
      citation:       'color:#60a5fa',   // blue
      citation_map:   'color:#60a5fa',
      thinking:       'color:#facc15',   // yellow
      validation:     'color:#facc15',
      agent_start:    'color:#a78bfa',   // purple
      agent_complete: 'color:#a78bfa',
      end:            'color:#a78bfa',
      error:          'color:#f87171',   // red
      agent_error:    'color:#f87171',
    }
    const style = COLORS[event] ?? 'color:#94a3b8'
    // For token events only print a dot to avoid flooding (every 20th token prints full data)
    if (event === 'token') {
      tokenCountRef.current++
      if (tokenCountRef.current % 20 === 1) {
        // eslint-disable-next-line no-console
        console.log(`%c[SSE] token #${tokenCountRef.current}`, style, data)
      }
    } else {
      // eslint-disable-next-line no-console
      console.log(`%c[SSE] ${event}`, style, data)
    }
  }

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
        setCurrentThreadId(null)
      }
    }
  }, [threadId, currentThreadId, setCurrentThreadId, messages.length])

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || isLoading) return

      try {
        // Add user message to UI immediately
        addUserMessage(content)
        setLoading(true)
        setError(null)
        
        // Reset agent history and streaming metrics for new conversation turn
        resetAgentHistory()
        resetStreamingMetrics()
        tokenCountRef.current = 0

        // Create AbortController for cancellation
        abortControllerRef.current = new AbortController()

        // Track streaming state
        let messageStarted = false

        // Pre-generate thread ID for new threads — this lets us update the URL via
        // window.history.replaceState() (no page transition) instead of router.push(),
        // which would tear down the page component during a live SSE stream.
        const effectiveThreadId = currentThreadId ?? (() => {
          const newId = crypto.randomUUID()
          setCurrentThreadId(newId)
          if (typeof window !== 'undefined') {
            window.history.replaceState({}, '', `/chat/${newId}`)
          }
          return newId
        })()
        const isNewThread = !currentThreadId

        // Optimistically insert a placeholder thread into the sidebar SWR cache
        // the instant the user hits send — before any network request fires.
        // The placeholder is replaced by the real DB row when the thread_title
        // event arrives or the end handler triggers a final revalidation.
        if (isNewThread) {
          const now = new Date()
          insertThreadOptimistically({
            id: effectiveThreadId,
            title: 'New Chat',
            preview: content.slice(0, 100),
            messageCount: 1,
            createdAt: now,
            updatedAt: now,
            userId: user?.id ?? '',
          })
        }

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
            thread_id: effectiveThreadId,
            is_new_thread: isNewThread,
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

            if (limit && remaining && reset) {
              const limitNum = parseInt(limit)
              const remainingNum = parseInt(remaining)
              const resetNum = parseInt(reset)

              // Skip if rate limiting is disabled (limit=0)
              if (limitNum === 0) {
                return
              }

              setRateLimit(limitNum, remainingNum, resetNum)
            }
          },
          onEvent: (event) => {
            // Parse and handle event
            switch (event.event) {
              case 'agent_start': {
                const data = parseSSEEvent('agent_start', event)
                if (data) {
                  logSSE('agent_start', { agent: data.agent, message: data.message })
                  startAgent(data.agent)
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
                  // Log every token (throttled to every 20th by logSSE)
                  logSSE('token', data.token)

                  // Ensure generator is marked as active when we receive tokens
                  const state = useChatStore.getState()
                  const currentAgentState = state.currentAgent
                  
                  if (currentAgentState !== 'generator') {
                    setCurrentAgent('generator')
                    const history = state.agentHistory
                    if (!history.some(a => a.name === 'generator')) {
                      startAgent('generator')
                    }
                  }

                  const sanitizedToken = sanitizeToken(data.token)
                  
                  if (!messageStarted) {
                    startStreamingMessage()
                    messageStarted = true
                  }
                  appendToStreamingMessage(sanitizedToken)
                }
                break
              }

              case 'token_reset': {
                // Legacy fallback — no longer emitted by backend. Keep as no-op.
                logSSE('token_reset', {})
                break
              }

              case 'citation': {
                const data = parseSSEEvent('citation', event)
                if (data) {
                  if (!isCitationSafe(data)) {
                    console.warn('[Security] Blocked unsafe citation:', data.chunk_id)
                    return
                  }

                  if (!messageStarted) {
                    startStreamingMessage()
                    messageStarted = true
                  }

                  const citation = {
                    document_id: data.document_id || data.chunk_id || 'unknown',
                    document_title: data.document_title || 'Unknown Document',
                    chunk_id: data.chunk_id,
                    content: data.preview || data.content || '',
                    similarity_score: data.score ?? data.similarity_score ?? undefined,
                    original_score: data.original_score ?? undefined,
                  }
                  logSSE('citation', { chunk_id: data.chunk_id, title: data.document_title, score: data.score })
                  addCitationToStreamingMessage(citation)
                }
                break
              }

              case 'agent_complete': {
                const data = parseSSEEvent('agent_complete', event)
                if (data) {
                  logSSE('agent_complete', { agent: data.agent })
                  completeAgent(data.agent)
                }
                break
              }

              case 'agent_error': {
                const data = parseSSEEvent('agent_error', event)
                if (data) {
                  logSSE('agent_error', { agent: data.agent, error: data.error })
                  errorAgent(data.agent)
                  toast.error(`Agent error: ${data.error}`)
                }
                break
              }

              case 'validation': {
                const data = parseSSEEvent('validation', event)
                if (data) {
                  logSSE('validation', {
                    passed: data.passed,
                    score: data.score,
                    issues: data.issues,
                  })
                  setQualityScore(data.score)
                }
                break
              }

              case 'thinking': {
                const data = parseSSEEvent('thinking', event)
                if (data) {
                  logSSE('thinking', { status: data.status, message: data.message, attempt: data.attempt })
                  if (data.status === 'complete') {
                    // Tokens are about to flow — clear the indicator.
                    setThinkingStatus(null)
                    // Ensure the streaming message placeholder exists.
                    if (!messageStarted) {
                      startStreamingMessage()
                      messageStarted = true
                    }
                  } else {
                    setThinkingStatus(data)
                    // Ensure a streaming message slot exists so the indicator
                    // has something to anchor to in the message list.
                    if (!messageStarted) {
                      startStreamingMessage()
                      messageStarted = true
                    }
                  }
                }
                break
              }

              case 'thread_title': {
                const data = parseSSEEvent('thread_title', event)
                if (data) {
                  logSSE('thread_title', { title: data.title })
                  updateThreadTitleOptimistically(effectiveThreadId, data.title)
                }
                break
              }

              case 'citation_map': {
                const data = parseSSEEvent('citation_map', event)
                if (data) {
                  if (typeof data.markers === 'object' && data.markers !== null) {
                    logSSE('citation_map', {
                      markerCount: Object.keys(data.markers).length,
                      keys: Object.keys(data.markers),
                    })
                    setCitationMapForMessage(data.markers)
                  } else {
                    console.warn('[SSE] citation_map event missing or invalid markers field, skipping')
                  }
                }
                break
              }

              case 'thread_created': {
                // With client-side UUID pre-generation, the thread ID is already set and
                // the URL already updated via replaceState before streaming started.
                // This event is kept for backward compatibility but we never redirect here —
                // router.push() during a live SSE stream causes a disruptive page transition.
                const data = parseSSEEvent('thread_created', event)
                if (data && data.thread_id) {
                  logSSE('thread_created', { thread_id: data.thread_id })
                  const liveState = useChatStore.getState()
                  if (!liveState.currentThreadId) {
                    setCurrentThreadId(data.thread_id)
                    if (typeof window !== 'undefined') {
                      window.history.replaceState({}, '', `/chat/${data.thread_id}`)
                    }
                  }
                } else {
                  console.error('[SSE] Invalid thread_created event data:', event.data)
                }
                break
              }

              case 'end': {
                const data = parseSSEEvent('end', event)
                if (data) {
                  logSSE('end', { success: data.success, thread_id: data.thread_id, error: data.error })

                  // Capture thread_id for multi-turn conversations
                  if (data.thread_id) {
                    if (!currentThreadId) {
                      setCurrentThreadId(data.thread_id)
                    }
                    // Refresh sidebar thread list after every turn.
                    // For new threads the title was already applied optimistically
                    // via the thread_title event — this just syncs any other fields.
                    mutateThreadHistory()
                  }

                  // Ensure message is started
                  if (!messageStarted) {
                    startStreamingMessage()
                    messageStarted = true
                  }
                  finishStreamingMessage()
                  setCurrentAgent(null)
                  setThinkingStatus(null)

                  if (!data.success && data.error) {
                    toast.error(`Chat failed: ${data.error}`)
                  }
                }
                break
              }

              case 'error': {
                const data = parseSSEEvent('error', event)
                if (data) {
                  logSSE('error', { error: data.error, details: data.details })
                  throw new Error(data.error)
                }
                break
              }

              default:
                logSSE(event.event, { raw: event.data?.slice(0, 120) })
            }
          },
          onError: (error, retryCount) => {
            console.error(`[SSE] Connection error (attempt ${retryCount}):`, error.message)
            if (retryCount === 1) {
              toast.error('Connection lost, retrying...')
            }
          },
          onReconnect: (retryCount) => {
            toast.info('Reconnecting...')
          },
        })

        sseClientRef.current = client

        // Connect and stream
        await client.connect()

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
        setThinkingStatus(null)
        abortControllerRef.current = null
        sseClientRef.current = null
      }
    },
    [
      isLoading,
      currentThreadId,
      user?.id,
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
      setThinkingStatus,
      setLoading,
      setError,
      setRateLimit,
      setCurrentThreadId,
    ]
  )

  /**
   * Cancel current streaming request
   */
  const cancelStream = useCallback(() => {
    if (abortControllerRef.current) {
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
    thinkingStatus,
    sendMessage,
    cancelStream,
    clearMessages,
  }
}
