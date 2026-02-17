import { NextRequest, NextResponse } from 'next/server'
import { auth } from '@clerk/nextjs/server'
import { apiFetch, apiJSON } from '@/lib/api-client'

/**
 * Backend document response type
 */
interface BackendDocument {
  id: string
  title: string
  source_id: string | null
  status: string
  chunk_count: number | null
  created_at: string
}

interface BackendDocumentListResponse {
  documents: BackendDocument[]
  total: number
}

/**
 * List all documents for the authenticated user
 * GET /api/documents
 */
export async function GET() {
  try {
    const { userId } = await auth()
    if (!userId) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      )
    }

    const response = await apiJSON('/api/v1/documents') as BackendDocumentListResponse
    
    // Transform backend response to match frontend expectations
    const transformedDocuments = response.documents.map((doc) => ({
      ...doc,
      filename: doc.title, // Backend uses 'title'
    }))
    
    return NextResponse.json({
      documents: transformedDocuments,
      total: response.total,
    })
  } catch (error) {
    console.error('Failed to fetch documents:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to fetch documents' },
      { status: 500 }
    )
  }
}

/**
 * Upload/ingest a new document
 * POST /api/documents
 */
export async function POST(request: NextRequest) {
  try {
    // Get user ID from Clerk
    const { userId } = await auth()
    if (!userId) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      )
    }

    // Get form data from request
    const formData = await request.formData()
    
    // Forward multipart form data to FastAPI with user_id query param
    const response = await apiFetch(`/api/v1/ingest?user_id=${userId}`, {
      method: 'POST',
      body: formData,
    })

    const data = await response.json()

    if (!response.ok) {
      return NextResponse.json(data, { status: response.status })
    }

    return NextResponse.json(data, { status: 201 })
  } catch (error) {
    console.error('Failed to upload document:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to upload document' },
      { status: 500 }
    )
  }
}

