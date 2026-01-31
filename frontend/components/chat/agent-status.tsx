/**
 * Agent status indicator
 * Shows which agent is currently processing
 */

'use client'

import { Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

interface AgentStatusProps {
  agent: string | null
  className?: string
}

const AGENT_LABELS: Record<string, string> = {
  router: 'Analyzing query',
  retriever: 'Searching documentation',
  generator: 'Generating response',
  validator: 'Validating quality',
}

export function AgentStatus({ agent, className }: AgentStatusProps) {
  if (!agent) return null

  const label = AGENT_LABELS[agent] || agent

  return (
    <div className={cn('flex items-center gap-2 text-sm text-muted-foreground', className)}>
      <Loader2 className="h-4 w-4 animate-spin" />
      <span>{label}...</span>
    </div>
  )
}
