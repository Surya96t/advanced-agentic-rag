import { NextRequest, NextResponse } from 'next/server'
import { apiFetch } from '@/lib/api-client'

/**
 * Backend chat request payload
 */
interface BackendChatRequest {
  message: string  // Backend expects 'message', not 'query'
  thread_id?: string
}

/**
 * Chat endpoint (SSE streaming)
 * POST /api/chat
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { message, thread_id } = body

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
    }

    const response = await apiFetch('/api/v1/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(backendRequest),
    })

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

        const decoder = new TextDecoder()
        let isClosed = false

        try {
          while (true) {
            const { done, value } = await reader.read()
            
            if (done) {
              if (!isClosed) {
                controller.close()
                isClosed = true
              }
              break
            }

            // Forward raw SSE chunks
            const chunk = decoder.decode(value, { stream: true })
            if (!isClosed) {
              controller.enqueue(new TextEncoder().encode(chunk))
            }
          }
        } catch (error) {
          console.error('Stream error:', error)
          if (!isClosed) {
            controller.error(error)
            isClosed = true
          }
        } finally {
          try {
            reader.releaseLock()
          } catch {
            // Reader might already be released
          }
        }
      },
    })

    // Return SSE stream
    return new Response(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    })
  } catch (error) {
    console.error('Chat error:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to process chat message' },
      { status: 500 }
    )
  }
}
