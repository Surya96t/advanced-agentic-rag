'use client'

import { useEffect, useState } from 'react'
import { AlertCircle, Clock } from 'lucide-react'
import { useRateLimitStore } from '@/stores/rate-limit-store'

export function RateLimitBanner() {
  const { limit, resetTime, isRateLimited } = useRateLimitStore()
  const [timeRemaining, setTimeRemaining] = useState<number>(0)

  useEffect(() => {
    console.log('[Rate Limit Banner] State changed:', {
      limit,
      resetTime,
      isRateLimited,
      resetDate: resetTime ? new Date(resetTime * 1000).toLocaleString() : null
    })
  }, [limit, resetTime, isRateLimited])

  useEffect(() => {
    if (!resetTime) {
      return
    }

    const updateTimer = () => {
      const now = Math.floor(Date.now() / 1000)
      const secondsLeft = Math.max(0, resetTime - now)
      setTimeRemaining(secondsLeft)
    }

    updateTimer()
    const interval = setInterval(updateTimer, 1000)

    return () => clearInterval(interval)
  }, [resetTime])

  // Don't show banner if not rate limited
  if (!isRateLimited || !resetTime || timeRemaining === 0) {
    console.log('[Rate Limit Banner] Hidden because:', {
      isRateLimited,
      hasResetTime: !!resetTime,
      timeRemaining,
      shouldShow: false
    })
    return null
  }

  const formatTime = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = seconds % 60

    if (hours > 0) {
      return `${hours}h ${minutes}m`
    }
    if (minutes > 0) {
      return `${minutes}m ${secs}s`
    }
    return `${secs}s`
  }

  return (
    <div className="border-b border-destructive/20 bg-destructive/10">
      <div className="container mx-auto px-4 py-3">
        <div className="flex items-center gap-3 text-sm">
          <AlertCircle className="h-5 w-5 text-destructive shrink-0" />
          <div className="flex-1">
            <p className="font-medium text-destructive">
              Rate limit exceeded
            </p>
            <p className="text-muted-foreground">
              You&apos;ve reached your limit of {limit} requests. Please wait before
              sending another message.
            </p>
          </div>
          <div className="flex items-center gap-2 text-destructive font-mono">
            <Clock className="h-4 w-4" />
            <span className="font-semibold">{formatTime(timeRemaining)}</span>
          </div>
        </div>
      </div>
    </div>
  )
}
