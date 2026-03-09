/**
 * Interactive expandable citation card component
 * Shows document title, relevance score, and expandable content
 */

'use client'

import { useState } from 'react'
import { ChevronDown, Copy, Check, FileDown, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { Citation } from '@/types/chat'

interface CitationCardProps {
  citation: Citation
  index: number
  /** Display label for the badge (e.g. chunk_index). Falls back to index+1. */
  label?: number
}

export function CitationCard({ citation, index, label }: CitationCardProps) {
  const displayLabel = label ?? (index + 1)
  const [isExpanded, setIsExpanded] = useState(false)
  const [isCopied, setIsCopied] = useState(false)
  const [isLoadingSource, setIsLoadingSource] = useState(false)

  // Use the reranked/final score first (mapped to similarity_score in frontend), fallback to original_score
  // In RRF/Reranking, the final 'score' is the high-quality one
  const score = citation.similarity_score ?? citation.original_score ?? 0
  const scorePercentage = Math.round(score * 100)

  // Color-coded pill by relevance
  const getPillColor = (percentage: number) => {
    if (percentage >= 90) return 'bg-green-500/10 text-green-700 dark:text-green-400 hover:bg-green-500/20'
    if (percentage >= 70) return 'bg-blue-500/10 text-blue-700 dark:text-blue-400 hover:bg-blue-500/20'
    if (percentage >= 50) return 'bg-yellow-500/10 text-yellow-700 dark:text-yellow-400 hover:bg-yellow-500/20'
    return 'bg-red-500/10 text-red-700 dark:text-red-400 hover:bg-red-500/20'
  }

  const handleCopy = async () => {
    await navigator.clipboard.writeText(citation.content)
    setIsCopied(true)
    setTimeout(() => setIsCopied(false), 2000)
  }

  const handleViewSource = async () => {
    // Open a placeholder popup synchronously — popups opened after an `await` are
    // blocked by browsers; a synchronous open is treated as a direct user gesture.
    // Note: noopener/noreferrer are intentionally omitted here because passing either
    // causes window.open() to return null (per spec), which would sever our reference
    // before we can navigate the popup to the signed URL.
    const popup = window.open('', '_blank')
    if (!popup) return

    setIsLoadingSource(true)
    try {
      const res = await fetch(`/api/documents/${citation.document_id}/signed-url`)
      if (!res.ok) {
        // No blob stored or endpoint error — fall back to the document detail page
        popup.location.href = `/documents/${citation.document_id}`
        return
      }
      const { url } = (await res.json()) as { url: string }
      popup.location.href = url
    } catch {
      // Network error — fall back gracefully
      popup.location.href = `/documents/${citation.document_id}`
    } finally {
      setIsLoadingSource(false)
    }
  }

  return (
    <div className="inline-block">
      {/* Collapsed Pill */}
      {!isExpanded ? (
        <button
          onClick={() => setIsExpanded(true)}
          className={cn(
            'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium transition-colors',
            getPillColor(scorePercentage)
          )}
          aria-expanded={isExpanded}
          aria-controls={`citation-content-${index}`}
          title={`${citation.document_title} (${scorePercentage}% match)`}
        >
          <span className="font-mono">[{displayLabel}]</span>
        </button>
      ) : (
        /* Expanded Card */
        <div 
          id={`citation-content-${index}`}
          className={cn(
            'inline-block max-w-md rounded-lg border bg-card p-3 shadow-lg animate-in zoom-in-95 duration-200'
          )}
        >
          {/* Header with Collapse Button */}
          <div className="flex items-start gap-2 mb-2">
            <button
              onClick={() => setIsExpanded(false)}
              className="shrink-0 p-1 hover:bg-accent rounded transition-colors"
              aria-label="Collapse citation"
            >
              <ChevronDown className="h-3 w-3 text-muted-foreground" />
            </button>
            
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="font-mono text-xs text-muted-foreground">[{displayLabel}]</span>
                <h4 className="font-medium text-xs truncate">
                  {citation.document_title}
                </h4>
                <Badge 
                  variant="secondary" 
                  className="text-[10px] h-4 px-1.5 shrink-0"
                  title="Similarity Score"
                >
                  {scorePercentage}%
                </Badge>
              </div>
            </div>
          </div>

          {/* Content */}
          <div className="pl-6 mb-2">
            <p className="text-xs text-foreground/80 leading-relaxed whitespace-pre-wrap line-clamp-4">
              {citation.content}
            </p>
          </div>

          {/* Action Buttons */}
          <div className="pl-6 flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleCopy}
              className="h-6 px-2 text-[10px]"
            >
              {isCopied ? (
                <>
                  <Check className="h-2.5 w-2.5 mr-1" />
                  Copied
                </>
              ) : (
                <>
                  <Copy className="h-2.5 w-2.5 mr-1" />
                  Copy
                </>
              )}
            </Button>

            <Button
              variant="ghost"
              size="sm"
              onClick={handleViewSource}
              disabled={isLoadingSource}
              className="h-6 px-2 text-[10px]"
            >
              {isLoadingSource ? (
                <>
                  <Loader2 className="h-2.5 w-2.5 mr-1 animate-spin" />
                  Loading
                </>
              ) : (
                <>
                  <FileDown className="h-2.5 w-2.5 mr-1" />
                  View Source
                </>
              )}
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
