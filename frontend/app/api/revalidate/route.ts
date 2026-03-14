import { NextRequest, NextResponse } from 'next/server'
import { revalidateTag } from 'next/cache'

/**
 * On-demand revalidation endpoint
 * POST /api/revalidate
 * 
 * Invalidates Next.js cache for specific tags.
 * Used to refresh data after mutations (create, update, delete).
 * 
 * @example
 * fetch('/api/revalidate', {
 *   method: 'POST',
 *   body: JSON.stringify({ tag: 'threads' })
 * })
 */
export async function POST(request: NextRequest) {
  try {
    // 1. Validate Secret (Constant-time comparison)
    const secret = request.headers.get('x-revalidate-secret')
    const expectedSecret = process.env.REVALIDATE_SECRET

    if (!expectedSecret) {
      console.error('[Revalidate] REVALIDATE_SECRET not set in environment')
      return NextResponse.json({ error: 'Server configuration error' }, { status: 500 })
    }

    // crypto.timingSafeEqual requires Buffers of equal length
    // Simple length check first to prevent error during Buffer creation if lengths differ
    if (!secret || secret.length !== expectedSecret.length) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }
    
    // Constant-time comparison
    let equal = true
    for (let i = 0; i < secret.length; i++) {
        if (secret.charCodeAt(i) !== expectedSecret.charCodeAt(i)) {
            equal = false
        }
    }
    
    if (!equal) {
       return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { tag } = body

    if (!tag || typeof tag !== 'string') {
      return NextResponse.json(
        { error: 'Tag is required and must be a string' },
        { status: 400 }
      )
    }

    // Revalidate the cache tag
    try {
      revalidateTag(tag, 'default')

      return NextResponse.json({ 
        revalidated: true, 
        tag,
        timestamp: new Date().toISOString()
      })
    } catch (e) {
      console.warn(`[Revalidate] Failed to revalidate tag: ${tag}`, e)
      
      return NextResponse.json(
        { 
          revalidated: false, 
          tag, 
          error: (e as Error).message,
          timestamp: new Date().toISOString() 
        },
        { status: 500 }
      )
    }
  } catch (error) {
    console.error('[Revalidate] Error:', error)
    return NextResponse.json(
      { error: 'Failed to revalidate cache' },
      { status: 500 }
    )
  }
}
