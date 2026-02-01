'use client'

import { ServerCrash, ArrowLeft, RefreshCw } from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'

/**
 * 500 Server Error page
 * Shown when the backend API returns a server error
 */
export default function ServerErrorPage() {
  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-background">
      <Card className="max-w-md w-full p-8">
        <div className="flex flex-col items-center text-center space-y-6">
          {/* Icon */}
          <div className="rounded-full bg-destructive/10 p-4">
            <ServerCrash className="h-12 w-12 text-destructive" />
          </div>

          {/* Message */}
          <div className="space-y-2">
            <h1 className="text-6xl font-bold text-muted-foreground">500</h1>
            <h2 className="text-2xl font-bold">Server Error</h2>
            <p className="text-muted-foreground">
              Our servers encountered an unexpected error. Our team has been notified.
            </p>
          </div>

          {/* Actions */}
          <div className="flex flex-col sm:flex-row gap-3 w-full">
            <Button 
              className="flex-1"
              onClick={() => window.location.reload()}
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              Try Again
            </Button>
            <Button asChild variant="outline" className="flex-1">
              <Link href="/">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Go Home
              </Link>
            </Button>
          </div>

          {/* Help Text */}
          <div className="w-full pt-4 border-t space-y-2">
            <h3 className="font-semibold text-sm">What can I do?</h3>
            <ul className="text-xs text-muted-foreground text-left space-y-1">
              <li>• Wait a few moments and try again</li>
              <li>• Check if the backend API is running</li>
              <li>• Contact support if the issue persists</li>
            </ul>
          </div>
        </div>
      </Card>
    </div>
  )
}
