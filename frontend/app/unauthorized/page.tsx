import { ShieldAlert, Home, LogIn } from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'

/**
 * 401 Unauthorized page
 * Displayed when user tries to access protected content without authentication
 */
export default function UnauthorizedPage() {
  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-background">
      <Card className="max-w-md w-full p-8">
        <div className="flex flex-col items-center text-center space-y-6">
          {/* 401 Icon */}
          <div className="rounded-full bg-destructive/10 p-4">
            <ShieldAlert className="h-12 w-12 text-destructive" />
          </div>

          {/* 401 Message */}
          <div className="space-y-2">
            <h1 className="text-6xl font-bold text-muted-foreground">401</h1>
            <h2 className="text-2xl font-bold">Unauthorized</h2>
            <p className="text-muted-foreground">
              You need to be signed in to access this page.
            </p>
          </div>

          {/* Actions */}
          <div className="flex flex-col sm:flex-row gap-3 w-full">
            <Button
              asChild
              className="flex-1"
              variant="default"
            >
              <Link href="/sign-in">
                <LogIn className="mr-2 h-4 w-4" />
                Sign In
              </Link>
            </Button>
            <Button
              asChild
              variant="outline"
              className="flex-1"
            >
              <Link href="/">
                <Home className="mr-2 h-4 w-4" />
                Go Home
              </Link>
            </Button>
          </div>
        </div>
      </Card>
    </div>
  )
}
