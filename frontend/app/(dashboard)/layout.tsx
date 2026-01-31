import Link from 'next/link'
import { FileText, MessageSquare, Upload } from 'lucide-react'
import { UserSync } from '@/components/auth/user-sync'
import { UserButtonWrapper } from '@/components/auth/user-button-wrapper'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="flex min-h-screen flex-col">
      <UserSync />
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-backdrop-filter:bg-background/60">
        <div className="container flex h-16 items-center">
          <div className="mr-4 flex">
            <Link href="/dashboard" className="mr-6 flex items-center space-x-2">
              <span className="text-xl font-bold">Integration Forge</span>
            </Link>
          </div>
          
          {/* Navigation */}
          <nav className="flex flex-1 items-center space-x-6 text-sm font-medium">
            <Link
              href="/documents"
              className="flex items-center space-x-2 text-foreground/60 transition-colors hover:text-foreground"
            >
              <FileText className="h-4 w-4" />
              <span>Documents</span>
            </Link>
            <Link
              href="/upload"
              className="flex items-center space-x-2 text-foreground/60 transition-colors hover:text-foreground"
            >
              <Upload className="h-4 w-4" />
              <span>Upload</span>
            </Link>
            <Link
              href="/chat"
              className="flex items-center space-x-2 text-foreground/60 transition-colors hover:text-foreground"
            >
              <MessageSquare className="h-4 w-4" />
              <span>Chat</span>
            </Link>
          </nav>

          {/* User Button */}
          <div className="flex items-center space-x-4">
            <UserButtonWrapper />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1">
        {children}
      </main>
    </div>
  )
}
