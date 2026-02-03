/**
 * Hook for rotating placeholder text with smooth transitions
 */

'use client'

import { useState, useEffect, useRef } from 'react'

const DEFAULT_PLACEHOLDERS = [
  'Ask a question about your documentation...',
  'Try: How do I authenticate with the API?',
  'Example: What endpoints are available?',
  'Tip: Press Cmd+K to focus input',
  'Ask about integration patterns...',
]

interface UsePlaceholderRotationConfig {
  /** Array of placeholder strings to rotate through */
  placeholders?: string[]
  /** Interval in milliseconds (default: 3000) */
  interval?: number
  /** Whether to pause rotation when input is focused */
  pauseOnFocus?: boolean
}

/**
 * Hook that rotates through placeholder text
 * Returns current placeholder and ref to attach to input
 */
export function usePlaceholderRotation({
  placeholders = DEFAULT_PLACEHOLDERS,
  interval = 3000,
  pauseOnFocus = true,
}: UsePlaceholderRotationConfig = {}) {
  const [currentIndex, setCurrentIndex] = useState(0)
  const [isPaused, setIsPaused] = useState(false)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Rotate placeholder text
  useEffect(() => {
    if (isPaused || placeholders.length <= 1) return

    const timer = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % placeholders.length)
    }, interval)

    return () => clearInterval(timer)
  }, [isPaused, interval, placeholders.length])

  // Pause rotation when input is focused
  useEffect(() => {
    if (!pauseOnFocus) return

    const input = inputRef.current
    if (!input) return

    const handleFocus = () => setIsPaused(true)
    const handleBlur = () => setIsPaused(false)

    input.addEventListener('focus', handleFocus)
    input.addEventListener('blur', handleBlur)

    return () => {
      input.removeEventListener('focus', handleFocus)
      input.removeEventListener('blur', handleBlur)
    }
  }, [pauseOnFocus])

  return {
    /** Current placeholder text */
    placeholder: placeholders[currentIndex],
    /** Ref to attach to the input element */
    inputRef,
    /** Current index in the placeholders array */
    currentIndex,
    /** Whether rotation is paused */
    isPaused,
  }
}
