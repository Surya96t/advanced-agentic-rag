/**
 * Message input component with auto-resizing textarea
 * GPT-style clean design without heavy borders
 */

'use client'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { useState, type FormEvent, type KeyboardEvent } from 'react'
import { CornerDownLeft, StopCircle } from 'lucide-react'

interface MessageInputProps {
  onSend: (message: string) => void
  onStop?: () => void
  disabled?: boolean
  isStreaming?: boolean
  placeholder?: string
}

export function MessageInput({
  onSend,
  onStop,
  disabled = false,
  isStreaming = false,
  placeholder = 'Ask a question about your documentation...',
}: MessageInputProps) {
  const [value, setValue] = useState('')

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const trimmed = value.trim()
    if (!trimmed || disabled) return
    
    onSend(trimmed)
    setValue('') // Clear input after sending
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Submit on Enter, newline on Shift+Enter
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (value.trim() && !disabled) {
        handleSubmit(e as unknown as FormEvent<HTMLFormElement>)
      }
    }
  }

  return (
    <div className="border-t bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <form onSubmit={handleSubmit} className="p-4 max-w-3xl mx-auto">
        <div className="flex items-end gap-2">
          <Textarea
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            className="min-h-15 max-h-50 resize-none flex-1 bg-muted/50 border-muted-foreground/20 focus-visible:ring-1"
            aria-label="Chat message input"
          />
          {isStreaming && onStop ? (
            <Button
              type="button"
              variant="outline"
              size="icon"
              onClick={onStop}
              title="Stop generation"
              className="shrink-0"
            >
              <StopCircle className="h-4 w-4" />
            </Button>
          ) : (
            <Button
              type="submit"
              size="icon"
              disabled={disabled || !value.trim()}
              className="shrink-0"
              aria-label={disabled ? "Sending message" : "Send message"}
            >
              <CornerDownLeft className="h-4 w-4" />
            </Button>
          )}
        </div>
      </form>
    </div>
  )
}
