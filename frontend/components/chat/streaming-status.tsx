/**
 * Streaming status component
 * Shows token count, speed, and quality metrics during streaming
 */

'use client'

import { cn } from '@/lib/utils'
import { Loader2, Zap, CheckCircle2, AlertCircle } from 'lucide-react'
import { Badge } from '@/components/ui/badge'

interface StreamingStatusProps {
  tokenCount: number
  tokensPerSecond: number
  qualityScore?: number
  isThinking?: boolean
  className?: string
}

/**
 * Get speed color based on tokens/second
 */
function getSpeedColor(tps: number): string {
  if (tps >= 30) return 'text-green-600 dark:text-green-500'
  if (tps >= 10) return 'text-yellow-600 dark:text-yellow-500'
  return 'text-red-600 dark:text-red-500'
}

export function StreamingStatus({
  tokenCount,
  tokensPerSecond,
  qualityScore,
  isThinking = false,
  className,
}: StreamingStatusProps) {
  // Don't show anything if no activity
  if (!isThinking && tokenCount === 0) return null

  return (
    <div className={cn('flex items-center gap-3 text-xs text-muted-foreground', className)}>
      {/* Thinking Animation */}
      {isThinking && tokenCount === 0 && (
        <div className="flex items-center gap-2 animate-in fade-in duration-300">
          <Loader2 className="h-3 w-3 animate-spin" />
          <span className="animate-pulse">Thinking...</span>
        </div>
      )}

      {/* Token Count */}
      {tokenCount > 0 && (
        <div className="flex items-center gap-1.5">
          <span className="font-mono font-medium">{tokenCount.toLocaleString()}</span>
          <span>tokens</span>
        </div>
      )}

      {/* Speed Indicator */}
      {tokenCount > 0 && tokensPerSecond > 0 && (
        <div className="flex items-center gap-1.5">
          <Zap className="h-3 w-3" />
          <span className={cn('font-mono font-medium', getSpeedColor(tokensPerSecond))}>
            {tokensPerSecond.toFixed(0)}
          </span>
          <span>tok/s</span>
        </div>
      )}

      {/* Quality Meter */}
      {qualityScore != null && (
        <Badge 
          variant={qualityScore >= 70 ? 'default' : 'destructive'}
          className="h-5 px-2 gap-1"
        >
          {qualityScore >= 70 ? (
            <CheckCircle2 className="h-3 w-3" />
          ) : (
            <AlertCircle className="h-3 w-3" />
          )}
          <span className="font-mono">
            {qualityScore.toFixed(0)}% quality
          </span>
        </Badge>
      )}
    </div>
  )
}
