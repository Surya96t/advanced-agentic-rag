/**
 * Message bubble component using AI Elements
 * Displays user and AI messages with markdown support, citations, timestamps, and follow-up suggestions
 */

'use client'

import { Message, MessageContent } from '@/components/ai-elements/message'
import { Suggestions, Suggestion } from '@/components/ai-elements/suggestion'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { cn } from '@/lib/utils'
import { Bot, User, Loader2 } from 'lucide-react'
import dynamic from 'next/dynamic'
import { CitationsList } from './citation'
import { AgentStatus } from './agent-status'
import { StreamingStatus } from './streaming-status'
import type { Message as MessageType } from '@/types/chat'
import type { AgentStep, StreamingMetrics } from '@/stores/chat-store'

// Dynamically import the markdown renderer to reduce initial bundle size
const MarkdownRenderer = dynamic(
  () => import('./markdown-renderer').then((mod) => mod.MarkdownRenderer),
  {
    loading: () => (
      <div className="flex items-center gap-2 text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span className="text-sm">Loading...</span>
      </div>
    ),
    ssr: false,
  }
)

interface MessageBubbleProps {
  message: MessageType
  isLatestAI?: boolean
  isStreaming?: boolean
  agentHistory?: AgentStep[]
  streamingMetrics?: StreamingMetrics
  onSuggestionClick?: (suggestion: string) => void
}

// AI-generated follow-up suggestions based on common documentation queries
const FOLLOW_UP_SUGGESTIONS = [
  "Show me code examples",
  "What are the best practices?",
  "How do I get started?",
  "What are the requirements?",
  "Tell me more about authentication",
]

export function MessageBubble({ 
  message, 
  isLatestAI = false, 
  isStreaming = false,
  agentHistory = [],
  streamingMetrics,
  onSuggestionClick 
}: MessageBubbleProps) {
  const isUser = message.role === 'user'

  return (
    <div className="flex gap-3 mb-4 w-full overflow-hidden">
      {/* Avatar */}
      <Avatar className="h-8 w-8 mt-1 shrink-0">
        <AvatarFallback className={cn(
          isUser ? 'bg-primary text-primary-foreground' : 'bg-muted'
        )}>
          {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
        </AvatarFallback>
      </Avatar>

      {/* Message using AI Elements */}
      <Message from={isUser ? 'user' : 'assistant'} className="flex-1 min-w-0 overflow-hidden">
        <MessageContent className="overflow-hidden">
          {/* Agent Status (Chain of Thought) - show at top when streaming */}
          {!isUser && isStreaming && agentHistory.length > 0 && (
            <div className="mb-4 space-y-2">
              <AgentStatus agentHistory={agentHistory} />
              {streamingMetrics && (
                <StreamingStatus
                  tokenCount={streamingMetrics.tokenCount}
                  tokensPerSecond={streamingMetrics.tokensPerSecond}
                  qualityScore={streamingMetrics.qualityScore ?? undefined}
                  isThinking={streamingMetrics.tokenCount === 0}
                />
              )}
            </div>
          )}

          {/* Message text */}
          {isUser ? (
            <p className="text-sm whitespace-pre-wrap wrap-break-word">{message.content}</p>
          ) : (
            <MarkdownRenderer content={message.content} />
          )}

          {/* Citations (AI messages only) */}
          {!isUser && message.citations && message.citations.length > 0 && (
            <CitationsList citations={message.citations} />
          )}

          {/* Follow-up suggestions (latest AI message only) */}
          {!isUser && isLatestAI && onSuggestionClick && (
            <div className="mt-4">
              <Suggestions>
                {FOLLOW_UP_SUGGESTIONS.map((suggestion) => (
                  <Suggestion
                    key={suggestion}
                    suggestion={suggestion}
                    onClick={onSuggestionClick}
                  />
                ))}
              </Suggestions>
            </div>
          )}

          {/* Timestamp */}
          <div className="text-xs text-muted-foreground mt-1">
            {message.timestamp.toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </div>
        </MessageContent>
      </Message>
    </div>
  )
}
