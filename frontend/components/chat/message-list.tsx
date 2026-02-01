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
  const viewportRef = useRef<HTMLDivElement>(null)
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true)

  // Auto-scroll to bottom when new messages arrive (only if user hasn't manually scrolled up)
  useEffect(() => {
    if (shouldAutoScroll || isLoading) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, currentAgent, isLoading, shouldAutoScroll])

  // Detect if user has scrolled up from the ScrollArea viewport
  const handleScroll = () => {
    const viewport = viewportRef.current
    if (!viewport) return

    // Calculate if user is at the bottom of the scroll area
    const isAtBottom = Math.abs(
      viewport.scrollHeight - viewport.clientHeight - viewport.scrollTop
    ) < 10
    
    setShouldAutoScroll(isAtBottom)
  }

  // Attach scroll listener to viewport after mount
  useEffect(() => {
    const viewport = viewportRef.current
    if (!viewport) return

    viewport.addEventListener('scroll', handleScroll)
    return () => viewport.removeEventListener('scroll', handleScroll)
  }, []) // handleScroll is stable, no need to include it

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
      <ScrollArea className="h-full px-4" ref={viewportRef}>
        <div className="py-4 space-y-4" role="log" aria-label="Chat messages" aria-live="polite">
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
