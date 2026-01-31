/**
 * Chat state management with Zustand
 */

import { create } from 'zustand'
import { Message, Citation } from '@/types/chat'

interface ChatState {
  messages: Message[]
  isLoading: boolean
  error: string | null
  currentAgent: string | null  // Track which agent is currently active
  streamingMessageId: string | null  // ID of message being streamed
  
  // Actions
  addMessage: (message: Message) => void
  addUserMessage: (content: string) => void
  addAssistantMessage: (content: string, citations?: Message['citations']) => void
  startStreamingMessage: () => string  // Start a new streaming message, returns ID
  appendToStreamingMessage: (token: string) => void  // Append token to streaming message
  addCitationToStreamingMessage: (citation: Citation) => void  // Add citation
  finishStreamingMessage: () => void  // Mark streaming as complete
  setCurrentAgent: (agent: string | null) => void  // Set active agent
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  clearMessages: () => void
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isLoading: false,
  error: null,
  currentAgent: null,
  streamingMessageId: null,

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
      
      return {
        messages: state.messages.map((msg) =>
          msg.id === state.streamingMessageId
            ? { ...msg, content: msg.content + token }
            : msg
        ),
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

  setLoading: (loading) =>
    set({ isLoading: loading }),

  setError: (error) =>
    set({ error }),

  clearMessages: () =>
    set({ messages: [], error: null, streamingMessageId: null, currentAgent: null }),
}))

