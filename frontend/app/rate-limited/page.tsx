'use client'

import { useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { Clock, ArrowLeft } from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'

/**
 * 429 Rate Limited page
 * Shown when user exceeds API rate limits
 */
export default function RateLimitedPage() {
  const searchParams = useSearchParams()
  const resetParam = searchParams.get('reset')
  
  // Parse reset time (Unix timestamp in seconds) - use useState to avoid impure function during render
  const [resetTime] = useState(() => {
    if (!resetParam) {
      return Date.now() + 60000
    }
    
    const parsed = parseInt(resetParam, 10)
    // Validate that parsed value is a finite number before using it
    if (Number.isFinite(parsed) && parsed > 0) {
      return parsed * 1000
    }
    
    // Fallback to default if invalid
    return Date.now() + 60000
  })
  
  const [timeRemaining, setTimeRemaining] = useState<number>(0)
  const [progressValue, setProgressValue] = useState<number>(0)

  useEffect(() => {
    // Declare interval first to avoid TDZ issues
    let interval: NodeJS.Timeout | null = null
    
    const updateCountdown = () => {
      const now = Date.now()
      const remaining = Math.max(0, resetTime - now)
      setTimeRemaining(remaining)
      
      // Calculate progress (inverse - starts at 100, goes to 0)
      const totalDuration = 3600000 // 1 hour in ms
      const progress = 100 - (remaining / totalDuration) * 100
      setProgressValue(Math.max(0, Math.min(100, progress)))
      
      if (remaining <= 0 && interval !== null) {
        clearInterval(interval)
        interval = null
      }
    }

    updateCountdown()
    interval = setInterval(updateCountdown, 1000)

    return () => {
      if (interval !== null) {
        clearInterval(interval)
      }
    }
  }, [resetTime])

  const formatTime = (ms: number) => {
    const seconds = Math.floor(ms / 1000)
    const minutes = Math.floor(seconds / 60)
    const hours = Math.floor(minutes / 60)
    
    if (hours > 0) {
      return `${hours}h ${minutes % 60}m`
    } else if (minutes > 0) {
      return `${minutes}m ${seconds % 60}s`
    } else {
      return `${seconds}s`
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-background">
      <Card className="max-w-md w-full p-8">
        <div className="flex flex-col items-center text-center space-y-6">
          {/* Icon */}
          <div className="rounded-full bg-yellow-500/10 p-4">
            <Clock className="h-12 w-12 text-yellow-500" />
          </div>

          {/* Message */}
          <div className="space-y-2">
            <h1 className="text-6xl font-bold text-muted-foreground">429</h1>
            <h2 className="text-2xl font-bold">Rate Limit Exceeded</h2>
            <p className="text-muted-foreground">
              You&apos;ve made too many requests. Please wait before trying again.
            </p>
          </div>

          {/* Countdown */}
          {timeRemaining > 0 ? (
            <div className="w-full space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Time remaining:</span>
                <span className="font-mono font-semibold">
                  {formatTime(timeRemaining)}
                </span>
              </div>
              <Progress value={progressValue} className="h-2" />
            </div>
          ) : (
            <div className="w-full p-3 bg-green-500/10 border border-green-500/20 rounded-md">
              <p className="text-sm text-green-600 dark:text-green-400 font-medium">
                ✓ Rate limit has reset! You can try again now.
              </p>
            </div>
          )}

          {/* Actions */}
          <div className="flex flex-col sm:flex-row gap-3 w-full">
            {timeRemaining <= 0 && (
              <Button 
                className="flex-1"
                onClick={() => window.location.reload()}
              >
                Try Again
              </Button>
            )}
            <Button asChild variant="outline" className="flex-1">
              <Link href="/">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Go Home
              </Link>
            </Button>
          </div>

          {/* Rate Limit Info */}
          <div className="w-full pt-4 border-t space-y-2 text-left">
            <h3 className="font-semibold text-sm">Rate Limits</h3>
            <ul className="text-xs text-muted-foreground space-y-1">
              <li>• Chat: 100 requests/hour</li>
              <li>• Document Upload: 20 requests/hour</li>
              <li>• Document List: 200 requests/hour</li>
            </ul>
          </div>
        </div>
      </Card>
    </div>
  )
}
