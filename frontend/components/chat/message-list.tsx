/**
 * Message list component
 * Displays chat messages with auto-scroll and agent status
 */

'use client'

import { useEffect, useRef, useState } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { MessageBubble } from './message-bubble'
import { AgentStatus } from './agent-status'
import type { Message } from '@/types/chat'

interface MessageListProps {
  messages: Message[]
  currentAgent?: string | null
  isLoading?: boolean
}

export function MessageList({ messages, currentAgent, isLoading }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true)

  // Auto-scroll to bottom when new messages arrive (only if user hasn't manually scrolled up)
  useEffect(() => {
    if (shouldAutoScroll || isLoading) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, currentAgent, isLoading, shouldAutoScroll])

  // Detect if user has scrolled up
  const handleScroll = (event: React.UIEvent<HTMLDivElement>) => {
    const element = event.currentTarget
    const isAtBottom = Math.abs(
      element.scrollHeight - element.clientHeight - element.scrollTop
    ) < 10
    setShouldAutoScroll(isAtBottom)
  }

  if (messages.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center text-muted-foreground">
          <p className="text-lg font-medium mb-2">Start a conversation</p>
          <p className="text-sm">
            Ask questions about your uploaded API documentation
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-hidden relative">
      <ScrollArea className="h-full px-4" onScrollCapture={handleScroll}>
        <div className="py-4 space-y-4">
          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}
          
          {/* Show agent status when streaming */}
          {isLoading && currentAgent && (
            <AgentStatus agent={currentAgent} className="ml-11" />
          )}
          
          {/* Invisible div for auto-scroll target */}
          <div ref={bottomRef} />
        </div>
      </ScrollArea>
    </div>
  )
}
