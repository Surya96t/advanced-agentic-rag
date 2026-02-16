/**
 * Agent status indicator using AI Elements Chain of Thought
 * Shows agent workflow pipeline with step-by-step progress
 */

'use client'

import { 
  ChainOfThought, 
  ChainOfThoughtContent,
  ChainOfThoughtHeader,
  ChainOfThoughtStep 
} from '@/components/ai-elements/chain-of-thought'
import { cn } from '@/lib/utils'
import type { AgentStep } from '@/stores/chat-store'

interface AgentStatusProps {
  agentHistory: AgentStep[]
  className?: string
}

const AGENT_CONFIG: Record<string, { label: string; description: string }> = {
  context_loader: { label: 'Context', description: 'Loading history' },
  classifier: { label: 'Classifier', description: 'Analyzing query' },
  simple_answer: { label: 'Direct Answer', description: 'Responding directly' },
  router: { label: 'Router', description: 'Routing query' },
  query_expander: { label: 'Expander', description: 'Optimizing search' },
  retriever: { label: 'Retriever', description: 'Searching docs' },
  generator: { label: 'Generator', description: 'Generating response' }, 
  validator: { label: 'Validator', description: 'Checking quality' },
}

// Order of appearance in the UI
const AGENT_ORDER = [
  'context_loader',
  'classifier', 
  'simple_answer',
  'router',
  'query_expander',
  'retriever',
  'generator',
  'validator'
] as const

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

  // Calculate active step for header
  // Use reverse finding to get the LATEST active step (e.g. generator rather than stuck retriever)
  const activeStep = [...agentHistory].reverse().find(s => s.status === 'active' || s.status === 'error') 
    || agentHistory[agentHistory.length - 1]
    
  const activeConfig = activeStep ? AGENT_CONFIG[activeStep.name] : null
  const headerLabel = activeConfig ? activeConfig.label : 'Agent Workflow'

  return (
    <ChainOfThought className={cn('w-full', className)} defaultOpen={false}>
      <ChainOfThoughtHeader>
        {headerLabel}
      </ChainOfThoughtHeader>
      <ChainOfThoughtContent>
        {AGENT_ORDER.map((agentKey) => {
          // Only show steps that have actually started or completed
          // This avoids showing the full pipeline when only a part of it runs (e.g. simple answer)
          if (!agentHistory.some(a => a.name === agentKey)) {
            return null
          }

          const config = AGENT_CONFIG[agentKey] || { 
            label: agentKey, 
            description: 'Processing' 
          }
          
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
