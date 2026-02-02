import { Sparkles } from 'lucide-react'

/**
 * Empty state for chat page
 * Clean, minimal design with clickable starter suggestions
 */

interface ChatEmptyStateProps {
  onSuggestionClick?: (suggestion: string) => void
}

const SUGGESTIONS = [
  "How do I authenticate with the API?",
  "What are the available endpoints?",
  "Show me code examples for user registration",
]

export function ChatEmptyState({ onSuggestionClick }: ChatEmptyStateProps) {
  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <div className="max-w-2xl w-full space-y-8">
        {/* Starter Suggestions */}
        <div className="space-y-4">
          <h3 className="text-sm font-medium text-muted-foreground">
            Try asking about your documentation:
          </h3>
          <div className="grid gap-3">
            {SUGGESTIONS.map((suggestion) => (
              <button
                key={suggestion}
                onClick={() => onSuggestionClick?.(suggestion)}
                className="flex items-start gap-3 p-4 text-left rounded-lg border bg-card hover:bg-accent/50 transition-colors"
              >
                <Sparkles className="h-5 w-5 text-primary mt-0.5 shrink-0" />
                <span className="text-sm">{suggestion}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
