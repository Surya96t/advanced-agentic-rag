import { NextResponse } from 'next/server'
import { apiFetch } from '@/lib/api-client'

/**
 * Health check endpoint - Proxies to FastAPI backend
 * GET /api/health
 */
export async function GET() {
  try {
    const response = await apiFetch('/health')
    const data = await response.json()
    
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    console.error('Health check failed:', error)
    return NextResponse.json(
      { status: 'error', message: 'Backend unavailable' },
      { status: 503 }
    )
  }
}
