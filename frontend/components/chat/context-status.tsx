/**
 * Context window status display component
 * Shows token usage with color-coded progress bar
 */

'use client'

import { cn } from '@/lib/utils'

interface ContextStatusProps {
  totalTokens: number
  maxTokens: number
  className?: string
}

export function ContextStatus({ totalTokens, maxTokens, className }: ContextStatusProps) {
  const percentage = maxTokens > 0 ? Math.max(0, Math.min((totalTokens / maxTokens) * 100, 100)) : 0
  const remaining = maxTokens - totalTokens

  // Color coding based on usage
  const color =
    percentage > 80
      ? 'text-red-500'
      : percentage > 60
        ? 'text-yellow-500'
        : 'text-green-500'

  const barColor =
    percentage > 80
      ? 'bg-red-500'
      : percentage > 60
        ? 'bg-yellow-500'
        : 'bg-green-500'

  return (
    <div className={cn('flex items-center gap-2 text-xs text-muted-foreground', className)}>
      {/* Progress bar */}
      <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden">
        <div
          className={cn('h-full transition-all duration-300', barColor)}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>

      {/* Token count */}
      <span className={color}>
        {totalTokens.toLocaleString()} / {maxTokens.toLocaleString()} tokens
      </span>

      {/* Remaining (optional) */}
      {percentage > 60 && (
        <span className={cn('text-xs', color)}>
          ({remaining.toLocaleString()} left)
        </span>
      )}
    </div>
  )
}
