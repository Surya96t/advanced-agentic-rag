/**
 * Citation badge component
 * Displays source document references
 */

import { Badge } from '@/components/ui/badge'
import { FileText } from 'lucide-react'
import type { Citation } from '@/types/chat'

interface CitationBadgeProps {
  citation: Citation
}

export function CitationBadge({ citation }: CitationBadgeProps) {
  return (
    <Badge
      variant="secondary"
      className="gap-1 text-xs font-normal"
    >
      <FileText className="h-3 w-3" />
      <span>{citation.document_title}</span>
      {citation.similarity_score != null && (
        <span className="text-muted-foreground">
          ({Math.round(citation.similarity_score * 100)}%)
        </span>
      )}
    </Badge>
  )
}

interface CitationsListProps {
  citations: Citation[]
}

export function CitationsList({ citations }: CitationsListProps) {
  if (!citations || citations.length === 0) {
    return null
  }

  return (
    <div className="flex flex-wrap gap-2 mt-2">
      {citations.map((citation, index) => (
        <CitationBadge
          key={`${citation.chunk_id}-${index}`}
          citation={citation}
        />
      ))}
    </div>
  )
}
