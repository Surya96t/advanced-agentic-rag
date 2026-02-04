/**
 * New chat page (no thread ID)
 * Allows users to start a new conversation
 * Thread will be created lazily on first message send
 * Route: /chat
 */

'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { MessageList } from '@/components/chat/message-list'
import { MessageInput } from '@/components/chat/message-input'
import { ChatEmptyState } from '@/components/chat/chat-empty-state'
import { RateLimitBanner } from '@/components/rate-limit-banner'
import { useChat } from '@/hooks/useChat'
import { useRateLimitStore } from '@/stores/rate-limit-store'
import { useChatStore } from '@/stores/chat-store'

export default function NewChatPage() {
  const router = useRouter()
  const { currentThreadId, clearMessages, setCurrentThreadId } = useChatStore()
  const { isRateLimited } = useRateLimitStore()
  const { messages, isLoading, agentHistory, streamingMetrics, sendMessage, cancelStream } = useChat()

  // Clear messages and thread ID when component mounts
  useEffect(() => {
    console.log('[NewChatPage] Initializing new chat (lazy creation)')
    clearMessages()
    setCurrentThreadId(null) // null = new thread will be created on first message
  }, [clearMessages, setCurrentThreadId])

  // If user somehow has a thread ID, redirect to thread page
  // This happens after the first message is sent and thread_created event is received
  useEffect(() => {
    if (currentThreadId) {
      console.log('[NewChatPage] Thread created, redirecting to:', currentThreadId)
      router.push(`/chat/${currentThreadId}`)
    }
  }, [currentThreadId, router])

  const hasMessages = messages.length > 0

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
        {hasMessages ? (
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
