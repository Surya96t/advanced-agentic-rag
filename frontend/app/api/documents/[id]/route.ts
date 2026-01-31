import { NextRequest, NextResponse } from 'next/server'
import { apiFetch } from '@/lib/api-client'

type RouteContext = {
  params: Promise<{ id: string }>
}

/**
 * Delete a document by ID
 * DELETE /api/documents/[id]
 */
export async function DELETE(
  request: NextRequest,
  context: RouteContext
) {
  try {
    const { id } = await context.params

    const response = await apiFetch(`/api/v1/documents/${id}`, {
      method: 'DELETE',
    })

    const data = await response.json()

    if (!response.ok) {
      return NextResponse.json(data, { status: response.status })
    }

    return NextResponse.json(data)
  } catch (error) {
    console.error('Failed to delete document:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to delete document' },
      { status: 500 }
    )
  }
}
