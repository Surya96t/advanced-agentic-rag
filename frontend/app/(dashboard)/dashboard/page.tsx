import Link from 'next/link'
import { ArrowRight } from 'lucide-react'

/**
 * Dashboard Page
 * 
 * Ultra-minimal, centered design
 */
export default function DashboardPage() {
  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-200px)]">
      <div className="w-full max-w-3xl px-6">
        {/* Header */}
        <div className="mb-20 text-center">
          <h1 className="text-4xl font-semibold tracking-tight mb-3">Dashboard</h1>
          <p className="text-muted-foreground">
            Upload documents and start chatting with your data
          </p>
        </div>      {/* Quick Actions - Side by Side */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-20">
        {/* Documents Link */}
        <Link
          href="/documents"
          className="group flex items-start justify-between py-5 px-4 -mx-4 rounded-lg transition-colors hover:bg-accent/50"
        >
          <div className="w-full">
            <h3 className="text-2xl font-semibold mb-2 pb-3 border-b">Documents</h3>
            <p className="text-sm text-muted-foreground mt-3">
              Upload and manage your documentation
            </p>
          </div>
          <ArrowRight className="h-5 w-5 text-muted-foreground opacity-0 transition-all group-hover:opacity-100 group-hover:translate-x-1 mt-1 ml-4 shrink-0" />
        </Link>

        {/* Chat Link */}
        <Link
          href="/chat"
          className="group flex items-start justify-between py-5 px-4 -mx-4 rounded-lg transition-colors hover:bg-accent/50"
        >
          <div className="w-full">
            <h3 className="text-2xl font-semibold mb-2 pb-3 border-b">Chat</h3>
            <p className="text-sm text-muted-foreground mt-3">
              Ask questions about your documents
            </p>
          </div>
          <ArrowRight className="h-5 w-5 text-muted-foreground opacity-0 transition-all group-hover:opacity-100 group-hover:translate-x-1 mt-1 ml-4 shrink-0" />
        </Link>
      </div>

        {/* Metrics */}
        <div>
          <h2 className="text-lg font-semibold mb-1 pb-3 border-b">Overview</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 pt-6">
            <div>
              <p className="text-3xl font-semibold mb-1.5">0</p>
              <p className="text-sm text-muted-foreground">Documents</p>
            </div>
            <div>
              <p className="text-3xl font-semibold mb-1.5">0</p>
              <p className="text-sm text-muted-foreground">Conversations</p>
            </div>
            <div>
              <p className="text-3xl font-semibold mb-1.5">0</p>
              <p className="text-sm text-muted-foreground">Queries</p>
            </div>
            <div>
              <p className="text-3xl font-semibold mb-1.5">0</p>
              <p className="text-sm text-muted-foreground">Chunks</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
