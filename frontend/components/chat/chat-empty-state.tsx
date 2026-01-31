import { MessageSquare, Sparkles, FileText } from 'lucide-react'

/**
 * Empty state for chat page
 * Displayed when user has no messages yet
 */
export function ChatEmptyState() {
  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <div className="max-w-md text-center space-y-6">
        {/* Icon */}
        <div className="flex justify-center">
          <div className="rounded-full bg-primary/10 p-6">
            <MessageSquare className="h-12 w-12 text-primary" />
          </div>
        </div>

        {/* Title & Description */}
        <div className="space-y-2">
          <h3 className="text-2xl font-bold">Start a Conversation</h3>
          <p className="text-muted-foreground">
            Ask questions about your API documentation and get AI-powered answers with source citations.
          </p>
        </div>

        {/* Suggestions */}
        <div className="space-y-3 text-left">
          <p className="text-sm font-medium text-muted-foreground">Try asking:</p>
          <div className="space-y-2">
            <div className="flex items-start gap-3 text-sm">
              <Sparkles className="h-4 w-4 text-primary mt-0.5 shrink-0" />
              <span className="text-muted-foreground">
                &quot;How do I authenticate with the API?&quot;
              </span>
            </div>
            <div className="flex items-start gap-3 text-sm">
              <Sparkles className="h-4 w-4 text-primary mt-0.5 shrink-0" />
              <span className="text-muted-foreground">
                &quot;What are the available endpoints?&quot;
              </span>
            </div>
            <div className="flex items-start gap-3 text-sm">
              <Sparkles className="h-4 w-4 text-primary mt-0.5 shrink-0" />
              <span className="text-muted-foreground">
                &quot;Show me code examples for user registration&quot;
              </span>
            </div>
          </div>
        </div>

        {/* Upload Reminder */}
        <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground bg-muted/50 p-3 rounded-lg">
          <FileText className="h-4 w-4 shrink-0" />
          <span>
            Make sure to upload your API documentation first
          </span>
        </div>
      </div>
    </div>
  )
}
