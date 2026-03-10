/**
 * Thinking indicator component
 * Displays server-driven generation/validation progress while tokens are buffered.
 * Reads thinkingStatus directly from the chat store.
 */

'use client'

import { cn } from '@/lib/utils'
import { Loader2, RefreshCw, CheckCircle2 } from 'lucide-react'
import { useChatStore } from '@/stores/chat-store'

const STATUS_CONFIG = {
  start: {
    icon: Loader2,
    label: 'Generating response…',
    iconClass: 'animate-spin',
    spin: false,
  },
  validating: {
    icon: Loader2,
    label: 'Verifying response quality…',
    iconClass: 'animate-spin',
    spin: false,
  },
  retrying: {
    icon: RefreshCw,
    label: null, // built dynamically from attempt/max_attempts
    iconClass: 'animate-spin',
    spin: false,
  },
  complete: {
    icon: CheckCircle2,
    label: null,
    iconClass: '',
    spin: false,
  },
} as const

export function ThinkingIndicator({ className }: { className?: string }) {
  const thinkingStatus = useChatStore((s) => s.thinkingStatus)

  if (!thinkingStatus || thinkingStatus.status === 'complete' || thinkingStatus.status === 'start') return null

  const config = STATUS_CONFIG[thinkingStatus.status as keyof typeof STATUS_CONFIG]
  if (!config) return null

  const label =
    thinkingStatus.status === 'retrying'
      ? `Improving response (attempt ${thinkingStatus.attempt}/${thinkingStatus.max_attempts})…`
      : (thinkingStatus.message ?? config.label)

  const Icon = config.icon

  return (
    <div
      className={cn(
        'flex items-center gap-2 text-xs text-muted-foreground',
        'animate-in fade-in duration-300 ml-12',
        className,
      )}
      aria-live="polite"
      aria-label={label ?? undefined}
    >
      <Icon className={cn('h-3 w-3 shrink-0', config.iconClass)} />
      {label && <span className="animate-pulse">{label}</span>}
    </div>
  )
}
