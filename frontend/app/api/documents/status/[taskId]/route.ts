import { NextRequest, NextResponse } from 'next/server'
import { auth } from '@clerk/nextjs/server'
import { apiFetch } from '@/lib/api-client'

/**
 * Poll the status of a background ingestion task.
 * GET /api/documents/status/:taskId
 *
 * Proxies to FastAPI GET /api/v1/ingest/status/:taskId.
 * Returns { task_id, status: "processing" | "success" | "failure", result?, error? }
 */
export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ taskId: string }> }
) {
  const { userId } = await auth()
  if (!userId) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const { taskId } = await params

  try {
    const response = await apiFetch(`/api/v1/ingest/status/${encodeURIComponent(taskId)}`)
    const data = await response.json()

    if (!response.ok) {
      return NextResponse.json(data, { status: response.status })
    }

    return NextResponse.json(data)
  } catch (error) {
    console.error('Failed to fetch task status:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to fetch task status' },
      { status: 500 }
    )
  }
}
