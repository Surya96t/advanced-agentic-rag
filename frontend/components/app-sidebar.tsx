"use client"

import * as React from "react"
import {
  Home,
  MessageSquare,
  FileText,
  MessageCircle,
  Layers,
  ChevronRight,
} from "lucide-react"

import { NavMain } from "@/components/nav-main"
import ProfileDropdown from "@/components/profile-dropdown"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarRail,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarGroupContent,
} from "@/components/ui/sidebar"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import Link from "next/link"

// Navigation data for Integration Forge
const data = {
  user: {
    name: "Loading...",
    email: "user@example.com",
    avatar: "/avatars/default.jpg",
  },
  navMain: [
    {
      title: "Home",
      url: "/dashboard",
      icon: Home,
      isActive: false,
    },
    {
      title: "Chat",
      url: "/chat",
      icon: MessageSquare,
      isActive: false,
    },
    {
      title: "Documents",
      url: "/documents",
      icon: FileText,
      isActive: false,
    },
    {
      title: "Feedback",
      url: "/feedback",
      icon: MessageCircle,
      isActive: false,
    },
  ],
}

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const [mounted, setMounted] = React.useState(false)
  
  React.useEffect(() => {
    setMounted(true)
  }, [])

  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        {/* App Logo/Branding */}
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <Link href="/dashboard" aria-label="Integration Forge - Go to dashboard">
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                  <Layers className="size-4" />
                </div>
                <div className="grid flex-1 text-left text-sm leading-tight">
                  <span className="truncate font-semibold">Integration Forge</span>
                  <span className="truncate text-xs">RAG Agent</span>
                </div>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        {/* Main Navigation */}
        <NavMain items={data.navMain} />

        {/* TODO: Conversation History (collapsible section) - Only render on client to avoid hydration mismatch */}
        {mounted && (
          <Collapsible defaultOpen={false} className="group/collapsible">
            <SidebarGroup>
              <SidebarGroupLabel asChild>
                <CollapsibleTrigger className="group/label">
                  Recent Conversations
                  <ChevronRight className="ml-auto transition-transform duration-200 group-data-[state=open]/collapsible:rotate-90" />
                </CollapsibleTrigger>
              </SidebarGroupLabel>
              <CollapsibleContent>
                <SidebarGroupContent>
                  <SidebarMenu>
                    <SidebarMenuItem>
                      <SidebarMenuButton>
                        <span className="text-xs text-muted-foreground">
                          Coming soon...
                        </span>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  </SidebarMenu>
                </SidebarGroupContent>
              </CollapsibleContent>
            </SidebarGroup>
          </Collapsible>
        )}
      </SidebarContent>

      <SidebarFooter>
        {/* User Profile with Theme Toggle */}
        {/*<ProfileDropdown />*/}
      </SidebarFooter>

      <SidebarRail />
    </Sidebar>
  )
}
