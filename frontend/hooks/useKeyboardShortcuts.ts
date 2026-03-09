/**
 * Hook for managing keyboard shortcuts in the chat interface
 * Handles: Cmd+K (focus), Cmd+/ (help), Esc (cancel), etc.
 */

'use client'

import { useEffect, useCallback, useRef } from 'react'

interface KeyboardShortcutsConfig {
  /** Focus the input field (Cmd/Ctrl + K) */
  onFocus?: () => void
  /** Cancel streaming (Cmd/Ctrl + Esc) */
  onCancel?: () => void
  /** Show help modal (Cmd/Ctrl + /) */
  onShowHelp?: () => void
  /** Edit last message (Up arrow when input empty) */
  onEditLastMessage?: () => void
  /** Submit message (Cmd/Ctrl + Enter) */
  onSubmit?: () => void
  /** Whether shortcuts are enabled */
  enabled?: boolean
}

/**
 * Custom hook for managing global keyboard shortcuts
 */
export function useKeyboardShortcuts({
  onFocus,
  onCancel,
  onShowHelp,
  onEditLastMessage,
  onSubmit,
  enabled = true,
}: KeyboardShortcutsConfig) {
  // Use refs to avoid recreating event listeners on every render
  const handlersRef = useRef({
    onFocus,
    onCancel,
    onShowHelp,
    onEditLastMessage,
    onSubmit,
  })

  // Update refs when handlers change
  useEffect(() => {
    handlersRef.current = {
      onFocus,
      onCancel,
      onShowHelp,
      onEditLastMessage,
      onSubmit,
    }
  }, [onFocus, onCancel, onShowHelp, onEditLastMessage, onSubmit])

  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0
    const modKey = isMac ? event.metaKey : event.ctrlKey
    const { onFocus, onCancel, onShowHelp, onSubmit } = handlersRef.current

    // Cmd/Ctrl + K → Focus input
    if (modKey && event.key === 'k') {
      event.preventDefault()
      onFocus?.()
      return
    }

    // Cmd/Ctrl + / → Show help
    if (modKey && event.key === '/') {
      event.preventDefault()
      onShowHelp?.()
      return
    }

    // Cmd/Ctrl + Enter → Submit (when input is focused)
    if (modKey && event.key === 'Enter') {
      const target = event.target as HTMLElement
      const isTextarea = target.tagName === 'TEXTAREA'
      const isInput = target.tagName === 'INPUT'
      
      if (isTextarea || isInput) {
        event.preventDefault()
        onSubmit?.()
      }
      return
    }

    // Cmd/Ctrl + Esc → Cancel streaming
    if (modKey && event.key === 'Escape') {
      onCancel?.()
      return
    }
  }, [])

  useEffect(() => {
    if (!enabled) return

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [enabled, handleKeyDown])

  return {
    /**
     * Returns the modifier key text based on platform (⌘ for Mac, Ctrl for others)
     */
    getModKey: () => {
      const isMac = typeof navigator !== 'undefined' && 
        navigator.platform.toUpperCase().indexOf('MAC') >= 0
      return isMac ? '⌘' : 'Ctrl'
    },
  }
}
