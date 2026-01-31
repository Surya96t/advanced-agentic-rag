import Link from 'next/link'
import { UserSync } from '@/components/auth/user-sync'
import { UserButtonWrapper } from '@/components/auth/user-button-wrapper'
import { DashboardNav } from '@/components/layout/dashboard-nav'

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
          <DashboardNav />

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
