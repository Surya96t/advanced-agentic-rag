/**
 * Agent status indicator using AI Elements Chain of Thought
 * Shows agent workflow pipeline with step-by-step progress
 */

'use client'

import { 
  ChainOfThought, 
  ChainOfThoughtContent,
  ChainOfThoughtStep 
} from '@/components/ai-elements/chain-of-thought'
import { cn } from '@/lib/utils'
import type { AgentStep } from '@/stores/chat-store'

interface AgentStatusProps {
  agentHistory: AgentStep[]
  className?: string
}

const AGENT_CONFIG = {
  router: { label: 'Router', description: 'Analyzing query complexity' },
  retriever: { label: 'Retriever', description: 'Searching documentation' },
  generator: { label: 'Generator', description: 'Generating response' },
  validator: { label: 'Validator', description: 'Validating quality' },
}

const AGENT_ORDER = ['router', 'retriever', 'generator', 'validator'] as const

/**
 * Format duration in milliseconds to human-readable string
 */
function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

/**
 * Determines the status of each agent step based on the agent history
 */
function getAgentStatus(
  agentHistory: AgentStep[], 
  agentKey: string
): 'complete' | 'active' | 'pending' {
  const agent = agentHistory.find(a => a.name === agentKey)
  
  if (!agent) return 'pending'
  // Map error to complete (visual will show it's done, even if with error)
  if (agent.status === 'error') return 'complete'
  return agent.status
}

/**
 * Get duration for completed agent
 */
function getAgentDuration(agentHistory: AgentStep[], agentKey: string): string | null {
  const agent = agentHistory.find(a => a.name === agentKey)
  
  if (!agent || !agent.duration) return null
  return formatDuration(agent.duration)
}

export function AgentStatus({ agentHistory, className }: AgentStatusProps) {
  // Show pipeline if we have any agent activity
  if (agentHistory.length === 0) return null

  return (
    <ChainOfThought className={cn('w-full', className)} defaultOpen={true}>
      <ChainOfThoughtContent>
        {AGENT_ORDER.map((agentKey) => {
          const config = AGENT_CONFIG[agentKey]
          const status = getAgentStatus(agentHistory, agentKey)
          const duration = getAgentDuration(agentHistory, agentKey)
          
          // Build description with duration if available
          const description = duration 
            ? `${config.description} (${duration})`
            : config.description
          
          return (
            <ChainOfThoughtStep
              key={agentKey}
              label={config.label}
              description={description}
              status={status}
            />
          )
        })}
      </ChainOfThoughtContent>
    </ChainOfThought>
  )
}
