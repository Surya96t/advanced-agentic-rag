import { Loader2 } from 'lucide-react'

/**
 * Dashboard loading state
 * Displayed while dashboard content is loading
 */
export default function DashboardLoading() {
  return (
    <div className="container mx-auto py-8 px-4">
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <Loader2 className="h-12 w-12 animate-spin text-primary" />
        <p className="text-muted-foreground">Loading...</p>
      </div>
    </div>
  )
}
