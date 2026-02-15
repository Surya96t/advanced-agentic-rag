/**
 * Chat state management with Zustand
 */

import { create } from 'zustand'
import { revalidateThreads } from '@/app/actions'
import { Message, Citation } from '@/types/chat'

/**
 * Generate a stable message ID based on content and timestamp
 * This ensures messages have consistent IDs across reloads
 * 
 * @param role - Message role (user/assistant)
 * @param content - Message content
 * @param timestamp - Message timestamp (use empty string if unknown for deterministic fallback)
 * @returns Deterministic UUID-like string
 */
function generateStableMessageId(role: string, content: string, timestamp: Date | string): string {
  // Create a stable string combining all unique message properties
  // Handle missing/empty timestamps deterministically
  const timestampStr = timestamp 
    ? (timestamp instanceof Date ? timestamp.toISOString() : timestamp)
    : ''
  const data = `${role}:${content}:${timestampStr}`
  
  // Simple hash function (FNV-1a)
  let hash = 2166136261
  for (let i = 0; i < data.length; i++) {
    hash ^= data.charCodeAt(i)
    hash = Math.imul(hash, 16777619)
  }
  
  // Convert to unsigned 32-bit integer
  hash = hash >>> 0
  
  // Format as UUID-like string (not a real UUID, but deterministic)
  // Format: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx (where 4 = version, y = variant)
  const hex = hash.toString(16).padStart(8, '0')
  
  // Use timestamp for time component if available, with validation for invalid dates
  let timestamp32: number
  if (timestampStr) {
    const parsedTime = new Date(timestampStr).getTime()
    // Check for NaN (invalid date) and fall back to hash-based value
    if (!isNaN(parsedTime)) {
      timestamp32 = parsedTime & 0xFFFFFFFF
    } else {
      // Invalid timestamp string - use hash for deterministic fallback
      timestamp32 = hash & 0xFFFFFFFF
    }
  } else {
    // No timestamp provided - use hash for deterministic value
    timestamp32 = hash & 0xFFFFFFFF
  }
  
  const timeHex = timestamp32.toString(16).padStart(8, '0')
  
  return `${hex}-${timeHex.slice(0, 4)}-4${timeHex.slice(4, 7)}-${hash.toString(16).slice(0, 4)}-${timeHex}${hex.slice(0, 4)}`
}

export interface AgentStep {
  name: string
  status: 'pending' | 'active' | 'complete' | 'error'
  startTime?: number
  endTime?: number
  duration?: number
}

export interface StreamingMetrics {
  tokenCount: number
  startTime: number | null
  lastTokenTime: number | null
  tokensPerSecond: number
  qualityScore: number | null
}

export interface Thread {
  id: string
  title: string
  preview?: string
  messageCount: number
  createdAt: Date
  updatedAt: Date
  userId: string
}

interface ChatState {
  messages: Message[]
  isLoading: boolean
  error: string | null
  currentAgent: string | null  // Track which agent is currently active
  agentHistory: AgentStep[]  // Track all agents with their status and timing
  streamingMessageId: string | null  // ID of message being streamed
  streamingMetrics: StreamingMetrics  // Track streaming performance metrics
  
  // Thread management
  currentThreadId: string | null  // Active conversation thread
  threads: Thread[]  // List of all user's threads
  isLoadingThreads: boolean  // Loading state for thread list
  
  // Actions
  addMessage: (message: Message) => void
  addUserMessage: (content: string) => void
  addAssistantMessage: (content: string, citations?: Message['citations']) => void
  startStreamingMessage: () => string  // Start a new streaming message, returns ID
  appendToStreamingMessage: (token: string) => void  // Append token to streaming message
  addCitationToStreamingMessage: (citation: Citation) => void  // Add citation
  finishStreamingMessage: () => void  // Mark streaming as complete
  setCurrentAgent: (agent: string | null) => void  // Set active agent
  startAgent: (agent: string) => void  // Start agent and add to history
  completeAgent: (agent: string) => void  // Mark agent as complete
  errorAgent: (agent: string) => void  // Mark agent as error
  resetAgentHistory: () => void  // Clear agent history
  setQualityScore: (score: number) => void  // Set validation quality score
  resetStreamingMetrics: () => void  // Reset streaming metrics
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  clearMessages: () => void
  
  // Thread management actions
  setCurrentThreadId: (threadId: string | null) => void
  loadThreads: () => Promise<void>
  createNewThread: (title?: string) => Promise<string>  // DEPRECATED
  createNewChat: () => void  // New method for lazy creation
  loadThread: (threadId: string) => Promise<void>
  deleteThread: (threadId: string) => Promise<void>
  updateThreadTitle: (threadId: string, title: string) => Promise<void>
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  isLoading: false,
  error: null,
  currentAgent: null,
  agentHistory: [],
  streamingMessageId: null,
  streamingMetrics: {
    tokenCount: 0,
    startTime: null,
    lastTokenTime: null,
    tokensPerSecond: 0,
    qualityScore: null,
  },
  
  // Thread management state
  currentThreadId: null,
  threads: [],
  isLoadingThreads: false,

  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),

  addUserMessage: (content) =>
    set((state) => ({
      messages: [
        ...state.messages,
        {
          id: crypto.randomUUID(),
          role: 'user',
          content,
          timestamp: new Date(),
        },
      ],
    })),

  addAssistantMessage: (content, citations) =>
    set((state) => ({
      messages: [
        ...state.messages,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content,
          citations,
          timestamp: new Date(),
        },
      ],
    })),

  startStreamingMessage: () => {
    const messageId = crypto.randomUUID()
    set((state) => ({
      streamingMessageId: messageId,
      messages: [
        ...state.messages,
        {
          id: messageId,
          role: 'assistant',
          content: '',
          citations: [],
          timestamp: new Date(),
        },
      ],
    }))
    return messageId
  },

  appendToStreamingMessage: (token) =>
    set((state) => {
      if (!state.streamingMessageId) return state
      
      const now = Date.now()
      const { streamingMetrics } = state
      
      // Initialize timing on first token
      const startTime = streamingMetrics.startTime ?? now
      const tokenCount = streamingMetrics.tokenCount + 1
      
      // Calculate tokens per second
      const elapsedSeconds = (now - startTime) / 1000
      const tokensPerSecond = elapsedSeconds > 0 ? tokenCount / elapsedSeconds : 0
      
      return {
        messages: state.messages.map((msg) =>
          msg.id === state.streamingMessageId
            ? { ...msg, content: msg.content + token }
            : msg
        ),
        streamingMetrics: {
          ...streamingMetrics,
          tokenCount,
          startTime,
          lastTokenTime: now,
          tokensPerSecond,
        },
      }
    }),

  addCitationToStreamingMessage: (citation) =>
    set((state) => {
      if (!state.streamingMessageId) return state
      
      return {
        messages: state.messages.map((msg) =>
          msg.id === state.streamingMessageId
            ? {
                ...msg,
                citations: [
                  ...(msg.citations || []),
                  citation,
                ],
              }
            : msg
        ),
      }
    }),

  finishStreamingMessage: () =>
    set({ streamingMessageId: null }),

  setCurrentAgent: (agent) =>
    set({ currentAgent: agent }),

  startAgent: (agent) =>
    set((state) => {
      const now = Date.now()
      
      // Check if agent already exists in history (shouldn't happen, but be safe)
      const existingIndex = state.agentHistory.findIndex(a => a.name === agent)
      
      if (existingIndex !== -1) {
        // Update existing agent to active
        return {
          currentAgent: agent,
          agentHistory: state.agentHistory.map((a, i) =>
            i === existingIndex
              ? { ...a, status: 'active' as const, startTime: now }
              : a
          ),
        }
      }
      
      // Add new agent to history
      return {
        currentAgent: agent,
        agentHistory: [
          ...state.agentHistory,
          {
            name: agent,
            status: 'active' as const,
            startTime: now,
          },
        ],
      }
    }),

  completeAgent: (agent) =>
    set((state) => {
      const now = Date.now()
      
      return {
        agentHistory: state.agentHistory.map((a) =>
          a.name === agent
            ? {
                ...a,
                status: 'complete' as const,
                endTime: now,
                duration: a.startTime ? now - a.startTime : undefined,
              }
            : a
        ),
      }
    }),

  errorAgent: (agent) =>
    set((state) => ({
      agentHistory: state.agentHistory.map((a) =>
        a.name === agent ? { ...a, status: 'error' as const } : a
      ),
    })),

  resetAgentHistory: () =>
    set({ agentHistory: [], currentAgent: null }),

  setQualityScore: (score) =>
    set((state) => ({
      streamingMetrics: {
        ...state.streamingMetrics,
        qualityScore: score,
      },
    })),

  resetStreamingMetrics: () =>
    set({
      streamingMetrics: {
        tokenCount: 0,
        startTime: null,
        lastTokenTime: null,
        tokensPerSecond: 0,
        qualityScore: null,
      },
    }),

  setLoading: (loading) =>
    set({ isLoading: loading }),

  setError: (error) =>
    set({ error }),

  clearMessages: () =>
    set({ 
      messages: [], 
      error: null, 
      streamingMessageId: null, 
      currentAgent: null, 
      agentHistory: [], 
      isLoading: false,
      streamingMetrics: {
        tokenCount: 0,
        startTime: null,
        lastTokenTime: null,
        tokensPerSecond: 0,
        qualityScore: null,
      },
    }),
  
  // Thread management actions
  setCurrentThreadId: (threadId) =>
    set({ currentThreadId: threadId }),
  
  loadThreads: async () => {
    // Only show loading state if we have no threads (initial load)
    // This prevents the "flash" when refreshing in the background
    if (get().threads.length === 0) {
      set({ isLoadingThreads: true })
    }
    
    console.log('[Store] Loading threads...')
    try {
      // Load threads from backend
      // Note: Client-side fetch ignores 'next' options like revalidate/tags
      // Caching should be handled by the API route or browser cache headers
      const response = await fetch('/api/threads', {
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      })
      
      if (!response.ok) {
        throw new Error('Failed to load threads')
      }
      
      const threads = await response.json()
      
      // Log thread titles for debugging "New Chat" issue
      if (threads.length > 0) {
        const titles = threads.slice(0, 3).map((t: any) => `${t.thread_id.slice(0,8)}:${t.title}`)
        console.log('[Store] Loaded threads titles (first 3):', titles)
      }
      
      // Convert date strings to Date objects and map backend field names
      const threadsWithDates = threads.map((thread: { 
        thread_id: string; 
        title: string; 
        preview?: string;
        message_count: number;
        created_at: string;
        updated_at: string;
        user_id: string;
      }) => {
        const mapped = {
          id: thread.thread_id,  // Backend uses thread_id, frontend uses id
          title: thread.title,
          preview: thread.preview,
          messageCount: thread.message_count,
          createdAt: new Date(thread.created_at),
          updatedAt: new Date(thread.updated_at),
          userId: thread.user_id,
        }
        // Safety check
        if (!mapped.id) {
          console.error('[Store] Thread mapping failed - missing id:', thread)
        }
        return mapped
      })
      
      console.log('[Store] Mapped threads:', threadsWithDates.map((t: Thread) => ({ id: t.id, title: t.title })))
      console.log('[Store] Processed threads:', threadsWithDates.length)
      set({ threads: threadsWithDates, isLoadingThreads: false })
    } catch (error) {
      console.error('[Store] Failed to load threads:', error)
      set({ isLoadingThreads: false, error: 'Failed to load conversations' })
    }
  },
  
  createNewThread: async (title?: string) => {
    // DEPRECATED: Use createNewChat() instead for lazy thread creation
    // This method is kept for backward compatibility but creates empty threads
    console.warn('[Store] createNewThread is deprecated. Use createNewChat() instead.')
    try {
      const response = await fetch('/api/threads', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ title: title || 'New Chat' }),
      })
      
      if (!response.ok) {
        throw new Error('Failed to create thread')
      }
      
      const { thread_id } = await response.json()
      
      // Clear current messages and set new thread
      set({
        currentThreadId: thread_id,
        messages: [],
        agentHistory: [],
        streamingMessageId: null,
      })
      
      // Refresh thread list
      await get().loadThreads()
      
      return thread_id
    } catch (error) {
      console.error('Failed to create thread:', error)
      set({ error: 'Failed to create new conversation' })
      throw error
    }
  },
  
  /**
   * Create a new chat (lazy creation - no API call)
   * Thread will be created on first message send
   * Note: Navigation to /chat should be handled by the caller
   */
  createNewChat: () => {
    console.log('[Store] Creating new chat (lazy creation)')
    set({
      currentThreadId: null, // null = new chat (thread created on first message)
      messages: [],
      agentHistory: [],
      streamingMessageId: null,
      error: null,
      currentAgent: null,
      isLoading: false,
    })
    // Reset streaming metrics
    get().resetStreamingMetrics()
  },
  
  loadThread: async (threadId: string) => {
    try {
      // CRITICAL: Don't overwrite messages during active streaming or when already on this thread
      // When redirecting from /chat to /chat/[threadId], the stream is ongoing
      // and messages are being added in real-time. Fetching from backend now
      // would return empty/partial messages and clear the streaming state.
      const currentState = get()
      
      // Skip loading if:
      // 1. Stream is active (streamingMessageId !== null) - for any thread
      // 2. Messages already exist AND we're already viewing this thread (no reload needed)
      // BUT allow loading when navigating to a DIFFERENT thread
      if (currentState.streamingMessageId !== null || 
          (currentState.messages.length > 0 && currentState.currentThreadId === threadId)) {
        console.log('[loadThread] Skipping load - stream active or already on this thread', {
          streaming: currentState.streamingMessageId !== null,
          messageCount: currentState.messages.length,
          currentThreadId: currentState.currentThreadId,
          requestedThreadId: threadId,
          isSameThread: currentState.currentThreadId === threadId
        })
        // Just update the threadId to match the URL, keep existing messages
        // Only do this if we're staying on the same thread
        if (currentState.currentThreadId === threadId) {
          set({ currentThreadId: threadId })
        }
        return
      }

      // Clear previous messages immediately if switching threads to prevent stale UI
      if (currentState.currentThreadId !== threadId) {
        set({ messages: [], currentThreadId: threadId, isLoading: true })
      } else {
        set({ isLoading: true })
      }
      
      const response = await fetch(`/api/threads/${threadId}`, {
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      })
      
      if (!response.ok) {
        throw new Error('Failed to load thread')
      }
      
      // Backend returns { metadata: {...}, messages: [...] }
      const threadDetail = await response.json()
      const messages = threadDetail.messages || []
      
      // Convert backend message format to frontend format
      const formattedMessages: Message[] = messages.map((msg: {
        id?: string;  // Backend-assigned ID (if present)
        role: 'user' | 'assistant';
        content: string;
        timestamp?: string;
        citations?: Citation[];
      }) => {
        // Use backend ID if present, otherwise generate stable ID
        // Fallback to empty string (not current time) to ensure deterministic IDs
        const messageId = msg.id || generateStableMessageId(
          msg.role,
          msg.content,
          msg.timestamp || ''  // Empty string = deterministic fallback (no timestamp)
        )
        
        return {
          id: messageId,
          role: msg.role,
          content: msg.content,
          timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date(),
          citations: msg.citations || [],
        }
      })
      
      set({
        currentThreadId: threadId,
        messages: formattedMessages,
        agentHistory: [],
        streamingMessageId: null,
        isLoading: false,
      })
    } catch (error) {
      console.error('Failed to load thread:', error)
      set({ error: 'Failed to load conversation', isLoading: false })
    }
  },
  
  deleteThread: async (threadId: string) => {
    try {
      // Capture current thread ID before async operations to prevent race conditions
      const prevCurrentThreadId = get().currentThreadId
      
      const response = await fetch(`/api/threads/${threadId}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      })
      
      if (!response.ok) {
        throw new Error('Failed to delete thread')
      }
      
      // Invalidate threads cache after deletion
      await revalidateThreads()
      
      // Refresh thread list
      await get().loadThreads()
      
      // If deleted thread was the current thread when deletion started, reset state
      // Use captured value to avoid race condition with concurrent thread switches
      if (prevCurrentThreadId === threadId) {
        set({
          currentThreadId: null,
          messages: [],
          agentHistory: [],
          streamingMessageId: null,
        })
      }
    } catch (error) {
      console.error('Failed to delete thread:', error)
      set({ error: 'Failed to delete conversation' })
      throw error
    }
  },
  
  updateThreadTitle: async (threadId: string, title: string) => {
    try {
      console.log('[Store] Updating thread title:', { threadId, title })
      
      const response = await fetch(`/api/threads/${threadId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ title }),
      })
      
      if (!response.ok) {
        const errorText = await response.text()
        console.error('[Store] Update failed:', {
          status: response.status,
          statusText: response.statusText,
          error: errorText
        })
        throw new Error(`Failed to update thread: ${response.status} ${errorText}`)
      }
      
      console.log('[Store] Thread title updated successfully')
            // Invalidate threads cache after update
      await revalidateThreads()
            // Refresh thread list to get updated title
      await get().loadThreads()
    } catch (error) {
      console.error('Failed to update thread title:', error)
      set({ error: 'Failed to update conversation title' })
      throw error
    }
  },
}))

