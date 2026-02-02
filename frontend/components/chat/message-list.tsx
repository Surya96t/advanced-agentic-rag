/**
 * Message list component
 * Displays chat messages with auto-scroll and agent status
 * Simple container - parent handles scrolling
 */

'use client'

import { useEffect, useRef } from 'react'
import { MessageBubble } from './message-bubble'
import { AgentStatus } from './agent-status'
import type { Message } from '@/types/chat'

interface MessageListProps {
  messages: Message[]
  currentAgent?: string | null
  isLoading?: boolean
  onSuggestionClick?: (suggestion: string) => void
}

export function MessageList({ 
  messages, 
  currentAgent, 
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
        {messages.map((message, index) => (
          <MessageBubble 
            key={message.id} 
            message={message}
            isLatestAI={!isLoading && index === lastAIMessageIndex}
            onSuggestionClick={onSuggestionClick}
          />
        ))}
        
        {/* Show agent status when streaming */}
        {isLoading && currentAgent && (
          <AgentStatus agent={currentAgent} className="ml-11" />
        )}
        
        {/* Invisible div for auto-scroll target */}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
