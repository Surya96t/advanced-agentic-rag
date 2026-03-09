import { NextRequest, NextResponse } from 'next/server'
import { apiFetch } from '@/lib/api-client'

type RouteContext = {
  params: Promise<{ id: string }>
}

/**
 * Get a signed URL for a document's original file
 * GET /api/documents/[id]/signed-url
 */
export async function GET(
  request: NextRequest,
  context: RouteContext
) {
  try {
    const { id } = await context.params

    const response = await apiFetch(`/api/v1/documents/${id}/signed-url`, {
      method: 'GET',
    })

    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      return NextResponse.json(data, { status: response.status })
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Failed to get signed URL:', error)
    return NextResponse.json(
      { error: 'Failed to get signed URL' },
      { status: 500 }
    )
  }
}
