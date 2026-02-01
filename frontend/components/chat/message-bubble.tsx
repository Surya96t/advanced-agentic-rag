/**
 * Message bubble component
 * Displays user and AI messages with markdown support
 */

'use client'

import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { cn } from '@/lib/utils'
import { Bot, User, Loader2 } from 'lucide-react'
import dynamic from 'next/dynamic'
import { CitationsList } from './citation'
import type { Message } from '@/types/chat'

// Dynamically import the markdown renderer to reduce initial bundle size
// This heavy component (react-markdown + plugins) is only loaded when needed
const MarkdownRenderer = dynamic(
  () => import('./markdown-renderer').then((mod) => mod.MarkdownRenderer),
  {
    loading: () => (
      <div className="flex items-center gap-2 text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span className="text-sm">Loading...</span>
      </div>
    ),
    ssr: false, // Client-side only (markdown rendering not needed for SSR)
  }
)

interface MessageBubbleProps {
  message: Message
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  return (
    <div
      className={cn(
        'flex gap-3 mb-4',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}
    >
      {/* Avatar */}
      <Avatar className="h-8 w-8 mt-1">
        <AvatarFallback className={cn(
          isUser ? 'bg-primary text-primary-foreground' : 'bg-muted'
        )}>
          {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
        </AvatarFallback>
      </Avatar>

      {/* Message Content */}
      <div
        className={cn(
          'flex flex-col gap-1 max-w-[80%]',
          isUser ? 'items-end' : 'items-start'
        )}
      >
        {/* Message Bubble */}
        <div
          className={cn(
            'rounded-lg px-4 py-2',
            isUser
              ? 'bg-primary text-primary-foreground'
              : 'bg-muted'
          )}
        >
          {isUser ? (
            // User message - plain text
            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
          ) : (
            // AI message - markdown rendering (lazy-loaded)
            <MarkdownRenderer content={message.content} />
          )}
        </div>

        {/* Citations (AI messages only) */}
        {!isUser && message.citations && message.citations.length > 0 && (
          <CitationsList citations={message.citations} />
        )}

        {/* Timestamp */}
        <span className="text-xs text-muted-foreground px-1">
          {message.timestamp.toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </span>
      </div>
    </div>
  )
}
