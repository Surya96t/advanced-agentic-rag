/**
 * Citation component with source grouping
 * Groups chunks under their parent document and renders expandable badges
 */

'use client'

import { CitationCard } from '@/components/chat/citation-card'
import { FileText } from 'lucide-react'
import type { Citation } from '@/types/chat'

interface CitationsListProps {
  citations: Citation[]
}

/** Group citations by document_id → { title, document_id, citations[] } */
function groupByDocument(citations: Citation[]) {
  const groups = new Map<string, { title: string; documentId: string; items: Citation[] }>()

  for (const c of citations) {
    const docId = c.document_id ?? 'unknown'
    if (!groups.has(docId)) {
      groups.set(docId, { title: c.document_title, documentId: docId, items: [] })
    }
    groups.get(docId)!.items.push(c)
  }

  // Sort groups by best score (descending)
  return [...groups.values()].sort((a, b) => {
    const bestA = Math.max(...a.items.map(i => i.original_score ?? i.similarity_score ?? 0))
    const bestB = Math.max(...b.items.map(i => i.original_score ?? i.similarity_score ?? 0))
    return bestB - bestA
  })
}

export function CitationsList({ citations }: CitationsListProps) {
  if (!citations || citations.length === 0) {
    return null
  }

  const groups = groupByDocument(citations)
  const docCount = groups.length
  const chunkCount = citations.length

  return (
    <div className="mt-3">
      <h3 className="text-xs font-medium text-muted-foreground mb-1.5">
        Sources ({docCount === 1 && chunkCount === 1
          ? '1 source'
          : docCount === chunkCount
            ? `${chunkCount} sources`
            : `${docCount} ${docCount === 1 ? 'document' : 'documents'}, ${chunkCount} chunks`})
      </h3>
      <div className="space-y-2">
        {groups.map((group) => {
          // Sort chunks by marker index (chunk_index), fallback to score
          const sortedItems = [...group.items].sort((a, b) => {
            if (a.chunk_index != null && b.chunk_index != null) return a.chunk_index - b.chunk_index
            return (b.original_score ?? 0) - (a.original_score ?? 0)
          })

          return (
            <div key={group.documentId} className="rounded-md border border-border/50 bg-muted/20 px-2.5 py-2">
              {/* Document header */}
              <div className="flex items-center gap-1.5 mb-1.5">
                <FileText className="h-3 w-3 text-muted-foreground shrink-0" />
                <span className="text-xs font-medium truncate" title={group.title}>
                  {group.title}
                </span>
                <span className="text-[10px] text-muted-foreground shrink-0">
                  ({sortedItems.length} {sortedItems.length === 1 ? 'chunk' : 'chunks'})
                </span>
              </div>
              {/* Chunk badges */}
              <div className="flex flex-wrap gap-1.5">
                {sortedItems.map((citation, idx) => (
                  <CitationCard
                    key={`${citation.chunk_id}-${idx}`}
                    citation={citation}
                    index={idx}
                    label={citation.chunk_index}
                  />
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
