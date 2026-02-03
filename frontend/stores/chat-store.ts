/**
 * Chat state management with Zustand
 */

import { create } from 'zustand'
import { Message, Citation } from '@/types/chat'

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

interface ChatState {
  messages: Message[]
  isLoading: boolean
  error: string | null
  currentAgent: string | null  // Track which agent is currently active
  agentHistory: AgentStep[]  // Track all agents with their status and timing
  streamingMessageId: string | null  // ID of message being streamed
  streamingMetrics: StreamingMetrics  // Track streaming performance metrics
  
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
}

export const useChatStore = create<ChatState>((set) => ({
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
}))

