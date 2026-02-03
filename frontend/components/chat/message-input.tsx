/**
 * Enhanced message input with rotating placeholder, keyboard shortcuts,
 * character count, and smooth animations
 */

'use client'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { useState, useRef, useEffect, type FormEvent, type KeyboardEvent } from 'react'
import { CornerDownLeft, StopCircle, Loader2 } from 'lucide-react'
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts'
import { usePlaceholderRotation } from '@/hooks/usePlaceholderRotation'
import { cn } from '@/lib/utils'

interface MessageInputProps {
  onSend: (message: string) => void
  onStop?: () => void
  disabled?: boolean
  isStreaming?: boolean
  placeholder?: string
  maxCharacters?: number
}

export function MessageInput({
  onSend,
  onStop,
  disabled = false,
  isStreaming = false,
  placeholder,
  maxCharacters = 8000, // ~2000 tokens (chars / 4)
}: MessageInputProps) {
  const [value, setValue] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const formRef = useRef<HTMLFormElement>(null)

  // Rotating placeholder
  const { placeholder: rotatingPlaceholder, inputRef: placeholderRef } = 
    usePlaceholderRotation({
      placeholders: placeholder 
        ? [placeholder] 
        : [
            'Ask a question about your documentation...',
            'Try: How do I authenticate with the API?',
            'Example: What endpoints are available?',
            'Tip: Press Cmd+K to focus input',
            'Ask about integration patterns...',
          ],
      interval: 3000,
      pauseOnFocus: true,
    })

  // Keyboard shortcuts
  const { getModKey } = useKeyboardShortcuts({
    onFocus: () => textareaRef.current?.focus(),
    onCancel: () => {
      if (isStreaming) onStop?.()
    },
    onSubmit: () => {
      if (value.trim() && !disabled) {
        handleSubmit()
      }
    },
    enabled: true,
  })

  // Character count warnings
  const charCount = value.length
  const charPercentage = (charCount / maxCharacters) * 100
  const showCharCount = charPercentage >= 80
  const charCountColor = 
    charPercentage >= 95 ? 'text-destructive' 
    : charPercentage >= 80 ? 'text-yellow-600 dark:text-yellow-500' 
    : 'text-muted-foreground'

  const handleSubmit = (e?: FormEvent<HTMLFormElement>) => {
    e?.preventDefault()
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
        handleSubmit()
      }
    }
  }

  // Sync refs for placeholder rotation
  useEffect(() => {
    if (textareaRef.current && placeholderRef) {
      placeholderRef.current = textareaRef.current
    }
  }, [placeholderRef])

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current
    if (!textarea) return

    textarea.style.height = 'auto'
    textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`
  }, [value])

  return (
    <div className="border-t bg-background/95 backdrop-blur supports-backdrop-filter:bg-background/60">
      <form 
        ref={formRef}
        onSubmit={handleSubmit} 
        className="p-4 max-w-3xl mx-auto"
      >
        <div className="flex flex-col gap-2">
          {/* Main input area */}
          <div className="flex items-end gap-2">
            <div className="relative flex-1">
              <Textarea
                ref={textareaRef}
                value={value}
                onChange={(e) => setValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={rotatingPlaceholder}
                disabled={disabled}
                maxLength={maxCharacters}
                className={cn(
                  "min-h-15 max-h-50 resize-none",
                  "bg-muted/50 border-muted-foreground/20",
                  "transition-all duration-200",
                  // Focus effects
                  "focus-visible:ring-2 focus-visible:ring-ring",
                  "focus-visible:border-transparent",
                  // Loading state - pulsing border
                  isStreaming && "animate-pulse border-primary/50",
                  // Disabled state
                  disabled && "opacity-50 cursor-not-allowed"
                )}
                aria-label="Chat message input"
                aria-describedby={showCharCount ? "char-count" : undefined}
              />
              
              {/* Character count indicator */}
              {showCharCount && (
                <div 
                  id="char-count"
                  className={cn(
                    "absolute bottom-2 right-2 text-xs font-mono",
                    "transition-colors duration-200",
                    charCountColor
                  )}
                  role="status"
                  aria-live="polite"
                >
                  {charCount.toLocaleString()} / {maxCharacters.toLocaleString()}
                </div>
              )}
            </div>

            {/* Send/Stop button */}
            {isStreaming && onStop ? (
              <Button
                type="button"
                variant="outline"
                size="icon"
                onClick={onStop}
                title={`Stop generation (${getModKey()}+Esc)`}
                className={cn(
                  "shrink-0 h-15 w-15",
                  "transition-all duration-200",
                  "hover:scale-105 active:scale-95"
                )}
              >
                <StopCircle className="h-5 w-5" />
              </Button>
            ) : (
              <Button
                type="submit"
                size="icon"
                disabled={disabled || !value.trim()}
                className={cn(
                  "shrink-0 h-15 w-15",
                  "transition-all duration-200",
                  !disabled && value.trim() && "hover:scale-105 active:scale-95"
                )}
                aria-label={
                  disabled 
                    ? "Sending message" 
                    : `Send message (${getModKey()}+Enter)`
                }
              >
                {disabled ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <CornerDownLeft className="h-5 w-5" />
                )}
              </Button>
            )}
          </div>

          {/* Keyboard shortcuts hint */}
          {!value && !isStreaming && (
            <p className="text-xs text-muted-foreground text-center animate-in fade-in duration-300">
              Press <kbd className="px-1.5 py-0.5 bg-muted rounded text-xs font-mono">{getModKey()}+K</kbd> to focus • 
              {' '}<kbd className="px-1.5 py-0.5 bg-muted rounded text-xs font-mono">{getModKey()}+Enter</kbd> to send
            </p>
          )}
        </div>
      </form>
    </div>
  )
}
