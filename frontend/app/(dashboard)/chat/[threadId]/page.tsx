/**
 * Individual chat thread page
 * Displays a specific conversation thread with its message history
 * Route: /chat/[threadId]
 */

'use client'

import { useEffect } from 'react'
import { useParams } from 'next/navigation'
import { MessageList } from '@/components/chat/message-list'
import { MessageInput } from '@/components/chat/message-input'
import { ChatEmptyState } from '@/components/chat/chat-empty-state'
import { RateLimitBanner } from '@/components/rate-limit-banner'
import { useChat } from '@/hooks/useChat'
import { useRateLimitStore } from '@/stores/rate-limit-store'
import { useChatStore } from '@/stores/chat-store'

export default function ChatThreadPage() {
  const params = useParams()
  const threadId = params.threadId as string
  
  const { messages, isLoading, agentHistory, streamingMetrics, sendMessage, cancelStream } = useChat(threadId)
  const { isRateLimited } = useRateLimitStore()
  const { loadThread, currentThreadId } = useChatStore()

  // Load thread when component mounts or threadId changes
  useEffect(() => {
    if (threadId && threadId !== currentThreadId) {
      console.log(`[ChatThreadPage] Loading thread: ${threadId}`)
      loadThread(threadId)
    }
  }, [threadId, currentThreadId, loadThread])

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
              : "Ask a question about your documentation..."
          }
        />
      </div>
    </>
  )
}
