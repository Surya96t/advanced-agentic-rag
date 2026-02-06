import { UserSync } from '@/components/auth/user-sync'
import { AppSidebar } from '@/components/app-sidebar'
import ProfileDropdown from '@/components/profile-dropdown'
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from '@/components/ui/sidebar'
import { Separator } from '@/components/ui/separator'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <SidebarProvider defaultOpen={false}>
      <UserSync />
      <AppSidebar />
      <SidebarInset>
        {/* Header with sidebar trigger */}
        <header className="flex h-16 shrink-0 items-center gap-2">
          <div className="flex items-center gap-2 px-4">
            <SidebarTrigger className="-ml-1" />
            <Separator orientation="vertical" className="mr-2 h-4" />
            {/*<h1 className="text-xl font-semibold">RAG System</h1>*/}
          </div>
          <div className="ml-auto px-4">
            <ProfileDropdown />
          </div>
        </header>

        {/* Main Content - Relative positioned container for chat's absolute positioning */}
        <main className="relative flex flex-1 flex-col gap-4 p-4 pt-0 min-h-0">
          {children}
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}
