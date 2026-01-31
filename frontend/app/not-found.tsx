import { FileQuestion, Home, Search } from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'

/**
 * 404 Not Found page
 * Displayed when a route doesn't exist
 */
export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-background">
      <Card className="max-w-md w-full p-8">
        <div className="flex flex-col items-center text-center space-y-6">
          {/* 404 Icon */}
          <div className="rounded-full bg-muted p-4">
            <FileQuestion className="h-12 w-12 text-muted-foreground" />
          </div>

          {/* 404 Message */}
          <div className="space-y-2">
            <h1 className="text-6xl font-bold text-muted-foreground">404</h1>
            <h2 className="text-2xl font-bold">Page Not Found</h2>
            <p className="text-muted-foreground">
              The page you&apos;re looking for doesn&apos;t exist or has been moved.
            </p>
          </div>

          {/* Actions */}
          <div className="flex flex-col sm:flex-row gap-3 w-full">
            <Button
              asChild
              className="flex-1"
              variant="default"
            >
              <Link href="/">
                <Home className="mr-2 h-4 w-4" />
                Go Home
              </Link>
            </Button>
            <Button
              asChild
              variant="outline"
              className="flex-1"
            >
              <Link href="/chat">
                <Search className="mr-2 h-4 w-4" />
                Start Chat
              </Link>
            </Button>
          </div>
        </div>
      </Card>
    </div>
  )
}
