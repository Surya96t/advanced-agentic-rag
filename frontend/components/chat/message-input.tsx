/**
 * Enhanced message input using PromptInput components.
 * Provides rotating placeholder, keyboard shortcuts, character count,
 * stop-generation button, and smooth animations.
 */

'use client'

import { useState, useRef, useEffect, type ChangeEvent, type KeyboardEvent } from 'react'
import { CornerDownLeft, StopCircle, Loader2 } from 'lucide-react'
import {
  PromptInput,
  PromptInputFooter,
  PromptInputTextarea,
  PromptInputButton,
  type PromptInputMessage,
} from '@/components/ai-elements/prompt-input'
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
  const [charCount, setCharCount] = useState(0)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

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

  // Keyboard shortcuts — PromptInputTextarea handles Enter/Cmd+Enter natively,
  // so we only register focus (Cmd+K) and cancel (Esc) here to avoid double submit.
  const { getModKey } = useKeyboardShortcuts({
    onFocus: () => textareaRef.current?.focus(),
    onCancel: () => {
      if (isStreaming) onStop?.()
    },
    enabled: true,
  })

  // Sync the placeholder rotation ref with the actual textarea element
  useEffect(() => {
    if (textareaRef.current && placeholderRef) {
      placeholderRef.current = textareaRef.current
    }
  }, [placeholderRef])

  // Character count state
  const charPercentage = (charCount / maxCharacters) * 100
  const showCharCount = charPercentage >= 80
  const charCountColor =
    charPercentage >= 95
      ? 'text-destructive'
      : charPercentage >= 80
        ? 'text-yellow-600 dark:text-yellow-500'
        : 'text-muted-foreground'

  const handleSubmit = (message: PromptInputMessage) => {
    const trimmed = message.text.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setCharCount(0)
  }

  // Prevent submission while streaming (PromptInputTextarea checks e.defaultPrevented)
  const handleTextareaKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (isStreaming && e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
    }
  }

  return (
    <div className="border-t bg-background/95 backdrop-blur supports-backdrop-filter:bg-background/60">
      <div className="p-4 max-w-3xl mx-auto">
        <PromptInput
          onSubmit={handleSubmit}
          className={cn(
            'bg-muted/50 border border-muted-foreground/20',
            'transition-all duration-200 rounded-lg',
            isStreaming && 'animate-pulse border-primary/50',
            disabled && 'opacity-50 cursor-not-allowed'
          )}
        >
          <PromptInputTextarea
            ref={textareaRef}
            placeholder={rotatingPlaceholder}
            disabled={disabled}
            maxLength={maxCharacters}
            onKeyDown={handleTextareaKeyDown}
            onChange={(e: ChangeEvent<HTMLTextAreaElement>) =>
              setCharCount(e.target.value.length)
            }
            aria-label="Chat message input"
            aria-describedby={showCharCount ? 'char-count' : undefined}
          />

          <PromptInputFooter>
            {/* Char count / keyboard hint */}
            <div className="flex items-center text-xs text-muted-foreground">
              {showCharCount ? (
                <span
                  id="char-count"
                  className={cn('font-mono transition-colors duration-200', charCountColor)}
                  role="status"
                  aria-live="polite"
                >
                  {charCount.toLocaleString()} / {maxCharacters.toLocaleString()}
                </span>
              ) : !isStreaming ? (
                <span>
                  <kbd className="px-1.5 py-0.5 bg-muted rounded text-xs font-mono">
                    {getModKey()}+K
                  </kbd>
                  {' '}to focus •{' '}
                  <kbd className="px-1.5 py-0.5 bg-muted rounded text-xs font-mono">
                    Enter
                  </kbd>
                  {' '}to send
                </span>
              ) : null}
            </div>

            {/* Send / Stop button */}
            {isStreaming && onStop ? (
              <PromptInputButton
                onClick={onStop}
                variant="outline"
                tooltip={{
                  content: 'Stop generation',
                  shortcut: `${getModKey()}+Esc`,
                }}
              >
                <StopCircle className="h-4 w-4" />
              </PromptInputButton>
            ) : (
              <PromptInputButton
                // type="submit" overrides the default type="button" in PromptInputButton
                type="submit"
                disabled={disabled || charCount === 0}
                tooltip={{
                  content: 'Send message',
                  shortcut: 'Enter',
                }}
              >
                {disabled ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <CornerDownLeft className="h-4 w-4" />
                )}
              </PromptInputButton>
            )}
          </PromptInputFooter>
        </PromptInput>
      </div>
    </div>
  )
}

