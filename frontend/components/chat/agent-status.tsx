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

interface AgentStatusProps {
  agent: string | null
  className?: string
}

const AGENT_CONFIG = {
  router: { label: 'Router', description: 'Analyzing query' },
  retriever: { label: 'Retriever', description: 'Searching documentation' },
  generator: { label: 'Generator', description: 'Generating response' },
  validator: { label: 'Validator', description: 'Validating quality' },
}

const AGENT_ORDER = ['router', 'retriever', 'generator', 'validator'] as const

/**
 * Determines the status of each agent step based on the current active agent
 */
function getAgentStatus(currentAgent: string | null, agentKey: string): 'complete' | 'active' | 'pending' {
  if (!currentAgent) return 'pending'
  
  const currentIndex = AGENT_ORDER.indexOf(currentAgent as typeof AGENT_ORDER[number])
  const agentIndex = AGENT_ORDER.indexOf(agentKey as typeof AGENT_ORDER[number])
  
  if (agentIndex < currentIndex) return 'complete'
  if (agentIndex === currentIndex) return 'active'
  return 'pending'
}

export function AgentStatus({ agent, className }: AgentStatusProps) {
  if (!agent) return null

  return (
    <ChainOfThought className={cn('w-full', className)}>
      <ChainOfThoughtContent>
        {AGENT_ORDER.map((agentKey) => {
          const config = AGENT_CONFIG[agentKey]
          const status = getAgentStatus(agent, agentKey)
          
          return (
            <ChainOfThoughtStep
              key={agentKey}
              label={config.label}
              description={config.description}
              status={status}
            />
          )
        })}
      </ChainOfThoughtContent>
    </ChainOfThought>
  )
}
