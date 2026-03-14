/**
 * New chat page (no thread ID)
 * Allows users to start a new conversation
 * Thread will be created lazily on first message send
 * Route: /chat
 */

'use client'

import { useEffect } from 'react'
import { MessageList } from '@/components/chat/message-list'
import { MessageInput } from '@/components/chat/message-input'
import { ChatEmptyState } from '@/components/chat/chat-empty-state'
import { RateLimitBanner } from '@/components/rate-limit-banner'
import { useChat } from '@/hooks/useChat'
import { useRateLimitStore } from '@/stores/rate-limit-store'
import { useChatStore } from '@/stores/chat-store'

export default function NewChatPage() {
  const { isRateLimited } = useRateLimitStore()
  const { currentThreadId, setCurrentThreadId, clearMessages } = useChatStore()
  // Don't pass threadId to useChat - we want a new chat
  const { messages, isLoading, agentHistory, streamingMetrics, sendMessage, cancelStream } = useChat()

  // CRITICAL: Ensure we're in new chat mode when this page mounts
  // This prevents stale thread IDs from appearing on /chat
  useEffect(() => {
    if (currentThreadId !== null) {
      setCurrentThreadId(null)
      clearMessages()
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps
  
  // IMPORTANT: On /chat (no thread ID), we should ALWAYS show empty state
  // Even if store has messages, they're from a previous thread
  // Only show messages if we're currently in a new thread (after thread_created event)
  const shouldShowMessages = currentThreadId !== null && messages.length > 0

  // Handle follow-up suggestion clicks
  const handleSuggestionClick = (suggestion: string) => {
    if (!isLoading && !isRateLimited) {
      sendMessage(suggestion)
    }
  }

  return (
    <>
      {/* Rate Limit Banner - Fixed at top */}
      <div className="shrink-0">
        <RateLimitBanner />
      </div>
      
      {/* Scrollable Messages Area - Takes all available space */}
      <div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden">
        {shouldShowMessages ? (
          <MessageList 
            messages={messages} 
            agentHistory={agentHistory}
            streamingMetrics={streamingMetrics}
            isLoading={isLoading}
            onSuggestionClick={handleSuggestionClick}
          />
        ) : (
          <ChatEmptyState onSuggestionClick={handleSuggestionClick} />
        )}
      </div>

      {/* Fixed Input at Bottom - Always visible */}
      <div className="shrink-0">
        <MessageInput
          onSend={sendMessage}
          onStop={cancelStream}
          disabled={isRateLimited}
          isStreaming={isLoading}
          placeholder={
            isRateLimited
              ? "Rate limit exceeded. Please wait..."
              : "Start a new conversation..."
          }
        />
      </div>
    </>
  )
}
