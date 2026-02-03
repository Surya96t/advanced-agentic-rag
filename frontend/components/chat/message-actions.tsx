/**
 * Message actions menu component
 * Shows hover actions: Copy, Regenerate, Delete
 */

'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { Copy, RotateCw, Trash2, Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'

interface MessageActionsProps {
  messageId: string
  content: string
  isUser: boolean
  onRegenerate?: () => void
  onDelete?: (messageId: string) => void
  className?: string
}

export function MessageActions({
  messageId,
  content,
  isUser,
  onRegenerate,
  onDelete,
  className,
}: MessageActionsProps) {
  const [isCopied, setIsCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content)
      setIsCopied(true)
      toast.success('Copied to clipboard')
      setTimeout(() => setIsCopied(false), 2000)
    } catch {
      toast.error('Failed to copy')
    }
  }

  const handleRegenerate = () => {
    onRegenerate?.()
    toast.info('Regenerating response...')
  }

  const handleDelete = () => {
    if (window.confirm('Delete this message? This action cannot be undone.')) {
      onDelete?.(messageId)
      toast.success('Message deleted')
    }
  }

  return (
    <TooltipProvider>
      <div
        className={cn(
          'flex items-center gap-1 p-1 rounded-md',
          'bg-background/95 backdrop-blur supports-backdrop-filter:bg-background/60',
          'border shadow-sm',
          'opacity-0 group-hover:opacity-100',
          'transition-opacity duration-200',
          className
        )}
      >
        {/* Copy Button */}
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={handleCopy}
            >
              {isCopied ? (
                <Check className="h-3.5 w-3.5 text-green-600" />
              ) : (
                <Copy className="h-3.5 w-3.5" />
              )}
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            <p>{isCopied ? 'Copied!' : 'Copy message'}</p>
          </TooltipContent>
        </Tooltip>

        {/* Regenerate Button (AI messages only) */}
        {!isUser && onRegenerate && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={handleRegenerate}
              >
                <RotateCw className="h-3.5 w-3.5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>Regenerate response</p>
            </TooltipContent>
          </Tooltip>
        )}

        {/* Delete Button */}
        {onDelete && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 hover:text-destructive"
                onClick={handleDelete}
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>Delete message</p>
            </TooltipContent>
          </Tooltip>
        )}
      </div>
    </TooltipProvider>
  )
}
