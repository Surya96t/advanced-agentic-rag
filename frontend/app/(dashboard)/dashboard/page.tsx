import Link from 'next/link'
import { ArrowRight } from 'lucide-react'
import { apiJSON } from '@/lib/api-client'
import { DashboardStats } from '@/types/dashboard'

async function getStats(): Promise<DashboardStats> {
  try {
    // In a BFF pattern, Server Components can technically call the external API directly
    // to avoid the loopback latency of calling its own Next.js API route,
    // while the /api/dashboard/stats route (created separately) serves external consumers.
    // 
    // Ideally, we would share the fetch logic in a lib/service, but calling apiJSON
    // here achieves the same result: ensuring the frontend acts as the strict gateway
    // for this view.
    return await apiJSON<DashboardStats>('/api/v1/stats/')
  } catch (error) {
    console.error('Failed to fetch dashboard stats:', error)
    return {
      documents_count: 0,
      chunks_count: 0,
      conversations_count: 0,
      queries_count: 0,
      total_tokens: 0,
      total_cost: 0,
      avg_latency_seconds: 0,
      error_rate: 0
    }
  }
}

/**
 * Dashboard Page
 * 
 * Ultra-minimal, centered design
 */
export default async function DashboardPage() {
  const stats = await getStats()

  // Formatters
  const formatCurrency = (val: number) => 
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 4 }).format(val)
  
  const formatCompact = (val: number) => 
    new Intl.NumberFormat('en-US', { notation: "compact", maximumFractionDigits: 1 }).format(val)

  const formatPercent = (val: number) => 
    new Intl.NumberFormat('en-US', { style: 'percent', maximumFractionDigits: 1 }).format(val)

  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-200px)]">
      <div className="w-full max-w-4xl px-6">
        {/* Header */}
        <div className="mb-16 text-center">
          <h1 className="text-4xl font-semibold tracking-tight mb-3">Dashboard</h1>
          <p className="text-muted-foreground">
            Upload documents and start chatting with your data
          </p>
        </div>

        {/* Quick Actions - Side by Side */}
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
          <h2 className="text-lg font-semibold mb-1 pb-3 border-b">System Overview</h2>
          
          {/* Row 1: Volume Counts */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 pt-6 pb-8 border-b border-dashed">
            <div>
              <p className="text-3xl font-semibold mb-1.5">{stats.documents_count}</p>
              <p className="text-sm text-muted-foreground">Documents</p>
            </div>
            <div>
              <p className="text-3xl font-semibold mb-1.5">{stats.chunks_count}</p>
              <p className="text-sm text-muted-foreground">Chunks</p>
            </div>
            <div>
              <p className="text-3xl font-semibold mb-1.5">{stats.conversations_count}</p>
              <p className="text-sm text-muted-foreground">Conversations</p>
            </div>
            <div>
              <p className="text-3xl font-semibold mb-1.5">{stats.queries_count}</p>
              <p className="text-sm text-muted-foreground">Total Queries</p>
            </div>
          </div>

          {/* Row 2: Performance & Cost (New) */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 pt-6">
            <div>
              <p className="text-3xl font-semibold mb-1.5 text-green-600 dark:text-green-500">
                {formatPercent(1 - stats.error_rate)}
              </p>
              <p className="text-sm text-muted-foreground">Success Rate</p>
            </div>
            <div>
              <p className="text-3xl font-semibold mb-1.5">{formatCompact(stats.total_tokens)}</p>
              <p className="text-sm text-muted-foreground">Total Tokens</p>
            </div>
            <div>
              <p className="text-3xl font-semibold mb-1.5">{stats.avg_latency_seconds.toFixed(2)}s</p>
              <p className="text-sm text-muted-foreground">Avg Latency</p>
            </div>
            <div>
              <p className="text-3xl font-semibold mb-1.5">{formatCurrency(stats.total_cost)}</p>
              <p className="text-sm text-muted-foreground">Est. Cost</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

