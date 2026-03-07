import { NextRequest, NextResponse } from 'next/server'
import { apiFetch } from '@/lib/api-client'

/**
 * Backend chat request payload
 */
interface BackendChatRequest {
  message: string  // Backend expects 'message', not 'query'
  thread_id?: string
  is_new_thread?: boolean
}

/**
 * Chat endpoint (SSE streaming)
 * POST /api/chat
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { message, thread_id, is_new_thread } = body

    if (!message || typeof message !== 'string') {
      return NextResponse.json(
        { error: 'Message is required' },
        { status: 400 }
      )
    }

    // Forward to FastAPI backend (streaming)
    const backendRequest: BackendChatRequest = {
      message: message,
      thread_id: thread_id,
      is_new_thread: is_new_thread,
    }

    const response = await apiFetch('/api/v1/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(backendRequest),
    })

    // Log headers in development only for debugging
    if (process.env.NODE_ENV === 'development') {
      const backendHeaders: Record<string, string> = {}
      response.headers.forEach((value, key) => {
        backendHeaders[key] = value
      })
      console.log('[API Route] Backend response headers:', backendHeaders)
    }

    if (!response.ok) {
      const errorText = await response.text()
      console.error('Backend error:', errorText)
      return NextResponse.json(
        { error: `Backend error: ${response.statusText}` },
        { status: response.status }
      )
    }

    // Check if response is SSE
    const contentType = response.headers.get('content-type')
    if (!contentType?.includes('text/event-stream')) {
      // Non-streaming response
      const data = await response.json()
      return NextResponse.json(data)
    }

    // Stream SSE response to frontend
    // Create a ReadableStream that forwards the backend SSE stream
    const stream = new ReadableStream({
      async start(controller) {
        const reader = response.body?.getReader()
        if (!reader) {
          controller.close()
          return
        }

        try {
          while (true) {
            const { done, value } = await reader.read()
            
            if (done) {
              controller.close()
              break
            }

            // Forward raw SSE chunks (no decoding/encoding needed)
            controller.enqueue(value)
          }
        } catch (error) {
          console.error('Stream error:', error)
          controller.error(error)
        } finally {
          try {
            reader.releaseLock()
          } catch {
            // Reader might already be released
          }
        }
      },
    })

    // Forward rate limit headers from backend
    const headers = new Headers({
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    })
    
    // Copy all rate limit headers (case-insensitive check)
    response.headers.forEach((value, key) => {
      if (key.toLowerCase().startsWith('x-ratelimit-')) {
        headers.set(key, value)
      }
    })

    // Return SSE stream with rate limit headers
    return new Response(stream, { headers })
  } catch (error) {
    console.error('Chat error:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to process chat message' },
      { status: 500 }
    )
  }
}
