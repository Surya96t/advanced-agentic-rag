/**
 * Message list component
 * Displays chat messages with auto-scroll and agent status
 * Simple container - parent handles scrolling
 */

'use client'

import { useEffect, useRef } from 'react'
import { MessageBubble } from './message-bubble'
import { ThinkingIndicator } from './thinking-indicator'
import type { Message } from '@/types/chat'
import type { AgentStep, StreamingMetrics } from '@/stores/chat-store'

interface MessageListProps {
  messages: Message[]
  agentHistory?: AgentStep[]
  streamingMetrics?: StreamingMetrics
  isLoading?: boolean
  onSuggestionClick?: (suggestion: string) => void
}

export function MessageList({ 
  messages, 
  agentHistory = [],
  streamingMetrics,
  isLoading,
  onSuggestionClick 
}: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length, isLoading])

  if (messages.length === 0) {
    return null
  }

  // Find the last AI message index
  const lastAIMessageIndex = messages.reduce((lastIndex, msg, index) => {
    return msg.role === 'assistant' ? index : lastIndex
  }, -1)

  return (
    <div className="px-4 py-4 w-full">
      <div className="space-y-4 max-w-4xl mx-auto w-full overflow-hidden">
        {messages.map((message, index) => {
          const isLatestAI = index === lastAIMessageIndex
          const isStreaming = isLoading && isLatestAI
          
          // Show agent history for the latest AI message (even after completion)
          // This allows users to review the chain of thought
          const showAgentHistory = isLatestAI && agentHistory.length > 0
          
          return (
            <MessageBubble 
              key={message.id} 
              message={message}
              isLatestAI={!isLoading && isLatestAI}
              isStreaming={isStreaming}
              agentHistory={showAgentHistory ? agentHistory : []}
              streamingMetrics={isStreaming ? streamingMetrics : undefined}
              onSuggestionClick={onSuggestionClick}
            />
          )
        })}
        
        {/* Thinking indicator — visible while tokens are buffered server-side */}
        {isLoading && <ThinkingIndicator className="pb-2" />}

        {/* Invisible div for auto-scroll target */}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
