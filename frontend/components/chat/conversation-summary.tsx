/**
 * Conversation summary display component
 * Shows summary of older messages when history is trimmed
 */

'use client'

import { History } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ConversationSummaryProps {
  summary: string
  messagesSummarized?: number
  className?: string
}

export function ConversationSummary({
  summary,
  messagesSummarized,
  className,
}: ConversationSummaryProps) {
  if (!summary) return null

  return (
    <div className={cn('mb-4 p-3 bg-muted/50 rounded-lg border border-border', className)}>
      <div className="flex items-start gap-2">
        <History className="w-4 h-4 mt-0.5 text-muted-foreground shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="text-xs font-medium text-muted-foreground mb-1">
            Earlier conversation
            {messagesSummarized && messagesSummarized > 0 && (
              <span className="ml-2 text-xs opacity-70">
                ({messagesSummarized} messages summarized)
              </span>
            )}
          </div>
          <p className="text-sm text-muted-foreground leading-relaxed">{summary}</p>
        </div>
      </div>
    </div>
  )
}
