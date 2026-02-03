"use client"

import { UserButton, useUser } from "@clerk/nextjs"
import {
  ChevronsUpDown,
} from "lucide-react"

import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"

export function NavUser({
  user,
}: {
  user: {
    name: string
    email: string
    avatar: string
  }
}) {
  const { user: clerkUser } = useUser()

  // Use Clerk user data if available, otherwise fallback to props
  const displayName = clerkUser?.fullName || user.name
  const displayEmail = clerkUser?.primaryEmailAddress?.emailAddress || user.email

  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <SidebarMenuButton
          size="lg"
          className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
          suppressHydrationWarning
        >
          <UserButton 
            afterSignOutUrl="/"
            appearance={{
              elements: {
                avatarBox: "h-8 w-8 rounded-lg"
              }
            }}
          />
          <div className="grid flex-1 text-left text-sm leading-tight" suppressHydrationWarning>
            <span className="truncate font-medium" suppressHydrationWarning>{displayName}</span>
            <span className="truncate text-xs" suppressHydrationWarning>{displayEmail}</span>
          </div>
          <ChevronsUpDown className="ml-auto size-4" />
        </SidebarMenuButton>
      </SidebarMenuItem>
    </SidebarMenu>
  )
}
