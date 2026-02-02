/**
 * Chat page
 * Main interface for conversational RAG
 * GPT-style clean layout with fixed input at bottom
 */

'use client'

import { MessageList } from '@/components/chat/message-list'
import { MessageInput } from '@/components/chat/message-input'
import { ChatEmptyState } from '@/components/chat/chat-empty-state'
import { RateLimitBanner } from '@/components/rate-limit-banner'
import { useChat } from '@/hooks/useChat'
import { useRateLimitStore } from '@/stores/rate-limit-store'

export default function ChatPage() {
  const { messages, isLoading, currentAgent, sendMessage, cancelStream } = useChat()
  const { isRateLimited } = useRateLimitStore()

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
            currentAgent={currentAgent}
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
