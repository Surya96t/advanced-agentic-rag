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
import { StreamingDebugOverlay } from '@/components/chat/streaming-debug-overlay'

export default function ChatThreadPage() {
  const params = useParams()
  const rawThreadId = params.threadId as string | undefined
  
  // Normalize threadId - handle undefined, null, empty string, or literal "undefined"
  // If threadId is the literal string "undefined", treat it as invalid
  const threadId = rawThreadId && rawThreadId !== 'undefined' ? rawThreadId : undefined
  
  const { messages, isLoading, agentHistory, streamingMetrics, sendMessage, cancelStream } = useChat(threadId || '')
  const { isRateLimited } = useRateLimitStore()
  const { loadThread } = useChatStore()

  // Load thread when component mounts or threadId changes
  // CRITICAL: Only load thread once when component mounts or threadId from URL changes
  // Do NOT react to store's currentThreadId changes to avoid race conditions
  useEffect(() => {
    // Validate threadId before attempting to load
    if (!threadId) {
      console.warn('[ChatThreadPage] Invalid or missing threadId:', rawThreadId)
      return
    }
    
    loadThread(threadId)
  }, [threadId, loadThread, rawThreadId]) // Include rawThreadId to detect string "undefined"

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

      {/* Dev-only streaming performance overlay */}
      <StreamingDebugOverlay streamingMetrics={streamingMetrics} />
    </>
  )
}
