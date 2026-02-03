/**
 * Citation component with expandable cards
 * Displays interactive source document references with similarity scores
 * 
 * Shows original_score (cosine similarity 0-1, higher = more relevant)
 * instead of RRF score (0-1, lower = better ranking)
 */

'use client'

import { CitationCard } from '@/components/chat/citation-card'
import type { Citation } from '@/types/chat'

interface CitationsListProps {
  citations: Citation[]
}

export function CitationsList({ citations }: CitationsListProps) {
  if (!citations || citations.length === 0) {
    return null
  }

  // Sort citations by relevance score (highest first)
  const sortedCitations = [...citations].sort((a, b) => {
    const scoreA = a.original_score ?? 0
    const scoreB = b.original_score ?? 0
    return scoreB - scoreA
  })

  return (
    <div className="mt-3">
      <h3 className="text-xs font-medium text-muted-foreground mb-1.5">
        Sources ({citations.length})
      </h3>
      <div className="flex flex-wrap gap-1.5">
        {sortedCitations.map((citation, index) => (
          <CitationCard 
            key={`${citation.chunk_id}-${index}`}
            citation={citation}
            index={index}
          />
        ))}
      </div>
    </div>
  )
}
