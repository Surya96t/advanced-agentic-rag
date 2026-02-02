/**
 * Citation component using AI Elements Sources
 * Displays collapsible source document references with similarity scores
 */

'use client'

import { Sources, SourcesTrigger, SourcesContent, Source } from '@/components/ai-elements/sources'
import { Badge } from '@/components/ui/badge'
import type { Citation } from '@/types/chat'

interface CitationsListProps {
  citations: Citation[]
}

export function CitationsList({ citations }: CitationsListProps) {
  if (!citations || citations.length === 0) {
    return null
  }

  return (
    <Sources>
      <SourcesTrigger count={citations.length} />
      <SourcesContent>
        {citations.map((citation, index) => (
          <div key={`${citation.chunk_id}-${index}`} className="flex items-center gap-2">
            <Source
              href={`/documents/${citation.document_id}`}
              title={citation.document_title}
            />
            {citation.similarity_score != null && (
              <Badge variant="secondary" className="text-xs shrink-0">
                {Math.round(citation.similarity_score * 100)}%
              </Badge>
            )}
          </div>
        ))}
      </SourcesContent>
    </Sources>
  )
}
