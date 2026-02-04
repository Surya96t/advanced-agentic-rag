import { NextRequest, NextResponse } from 'next/server'
import { apiFetch } from '@/lib/api-client'

/**
 * List all threads for current user
 * GET /api/threads
 */
export async function GET() {
  try {
    const response = await apiFetch('/api/v1/threads', {
      method: 'GET',
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('Backend error:', errorText)
      return NextResponse.json(
        { error: `Backend error: ${response.statusText}` },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Failed to fetch threads:', error)
    return NextResponse.json(
      { error: 'Failed to fetch threads' },
      { status: 500 }
    )
  }
}

/**
 * Create a new thread
 * POST /api/threads
 * 
 * DEPRECATED: Use lazy thread creation instead (send message with thread_id: null)
 * This endpoint creates empty threads which is not recommended.
 * Kept for backward compatibility only.
 */
export async function POST(request: NextRequest) {
  console.warn('[API] POST /api/threads is deprecated. Use lazy thread creation instead.')
  
  try {
    const body = await request.json()

    const response = await apiFetch('/api/v1/threads', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('Backend error:', errorText)
      return NextResponse.json(
        { error: `Backend error: ${response.statusText}` },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Failed to create thread:', error)
    return NextResponse.json(
      { error: 'Failed to create thread' },
      { status: 500 }
    )
  }
}
