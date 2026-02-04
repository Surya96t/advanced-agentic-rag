"use client"

import * as React from "react"
import {
  Home,
  MessageSquare,
  FileText,
  MessageCircle,
  Layers,
  ChevronRight,
  Plus,
  Trash2,
  Pencil,
} from "lucide-react"
import { useRouter } from "next/navigation"

import { NavMain } from "@/components/nav-main"
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
import { useChatStore } from "@/stores/chat-store"
import { formatDistanceToNow } from "date-fns"
import { cn } from "@/lib/utils"

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
  const [editingThreadId, setEditingThreadId] = React.useState<string | null>(null)
  const [editingTitle, setEditingTitle] = React.useState('')
  const router = useRouter()
  const { threads, isLoadingThreads, currentThreadId, loadThreads, deleteThread, createNewChat, updateThreadTitle } = useChatStore()
  
  React.useEffect(() => {
    setMounted(true)
    // Load threads when component mounts
    console.log('[Sidebar] Component mounted, loading threads...')
    loadThreads()
  }, [loadThreads])
  
  // Log when threads change
  React.useEffect(() => {
    console.log('[Sidebar] Threads updated:', threads.length, 'threads')
    console.log('[Sidebar] Current thread ID:', currentThreadId)
  }, [threads, currentThreadId])
  
  const handleNewChat = () => {
    console.log('[Sidebar] New Chat clicked - using lazy creation')
    
    // Use new lazy creation method (no API call)
    createNewChat()
    
    // Navigate to /chat (no thread_id) - thread will be created on first message
    router.push('/chat')
  }
  
  const handleThreadClick = (threadId: string) => {
    console.log('[Sidebar] Thread clicked:', threadId)
    if (!threadId || threadId === 'undefined') {
      console.error('[Sidebar] Invalid thread ID:', threadId)
      return
    }
    
    // Navigate to thread route
    router.push(`/chat/${threadId}`)
  }
  
  const handleDeleteThread = async (e: React.MouseEvent, threadId: string) => {
    e.stopPropagation()
    if (confirm('Delete this conversation?')) {
      await deleteThread(threadId)
      
      // If we deleted the current thread, navigate to /chat
      if (threadId === currentThreadId) {
        router.push('/chat')
      }
    }
  }
  
  const handleStartEdit = (e: React.MouseEvent, threadId: string, currentTitle: string) => {
    e.stopPropagation()
    setEditingThreadId(threadId)
    setEditingTitle(currentTitle)
  }
  
  const handleSaveEdit = async (threadId: string) => {
    const trimmedTitle = editingTitle.trim()
    
    // Validate title
    if (!trimmedTitle) {
      console.log('[Sidebar] Empty title, canceling edit')
      handleCancelEdit()
      return
    }
    
    // Check if title actually changed
    const currentThread = threads.find(t => t.id === threadId)
    if (trimmedTitle === currentThread?.title) {
      console.log('[Sidebar] Title unchanged, canceling edit')
      handleCancelEdit()
      return
    }
    
    console.log('[Sidebar] Saving new title:', trimmedTitle)
    
    try {
      await updateThreadTitle(threadId, trimmedTitle)
      setEditingThreadId(null)
      setEditingTitle('')
    } catch (error) {
      console.error('[Sidebar] Failed to save title:', error)
      // Keep edit mode open on error so user can retry
    }
  }
  
  const handleCancelEdit = () => {
    setEditingThreadId(null)
    setEditingTitle('')
  }
  
  const handleKeyDown = (e: React.KeyboardEvent, threadId: string) => {
    if (e.key === 'Enter') {
      handleSaveEdit(threadId)
    } else if (e.key === 'Escape') {
      handleCancelEdit()
    }
  }

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

        {/* Conversation History (collapsible section) - Only render on client to avoid hydration mismatch */}
        {mounted && (
          <Collapsible defaultOpen={true} className="group/collapsible">
            <SidebarGroup>
              <SidebarGroupLabel asChild>
                <CollapsibleTrigger className="group/label">
                  Recent Conversations
                  <ChevronRight className="ml-auto transition-transform duration-200 group-data-[state=open]/collapsible:rotate-90" />
                </CollapsibleTrigger>
              </SidebarGroupLabel>
              <CollapsibleContent>
                <SidebarGroupContent>
                  {/* New Chat Button */}
                  <div className="px-2 pb-2">
                    <button
                      onClick={handleNewChat}
                      className={cn(
                        "w-full flex items-center gap-2 px-3 py-2 text-sm rounded-md transition-colors",
                        currentThreadId === null
                          ? "bg-primary text-primary-foreground"
                          : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
                      )}
                      aria-label="Start a new chat"
                    >
                      <Plus className="h-4 w-4" />
                      <span>New Chat</span>
                    </button>
                  </div>
                  
                  <SidebarMenu>
                    {isLoadingThreads ? (
                      <SidebarMenuItem key="loading">
                        <SidebarMenuButton disabled>
                          <span className="text-xs text-muted-foreground">Loading...</span>
                        </SidebarMenuButton>
                      </SidebarMenuItem>
                    ) : threads.length === 0 ? (
                      <SidebarMenuItem key="empty">
                        <SidebarMenuButton disabled>
                          <span className="text-xs text-muted-foreground">No conversations yet</span>
                        </SidebarMenuButton>
                      </SidebarMenuItem>
                    ) : (
                      threads.map((thread) => {
                        const isEditing = editingThreadId === thread.id
                        
                        return (
                          <SidebarMenuItem key={thread.id}>
                            <div className={cn(
                              "group/thread flex items-center gap-2 w-full rounded-md transition-colors",
                              thread.id === currentThreadId ? "bg-accent" : "hover:bg-accent/50"
                            )}>
                              <SidebarMenuButton
                                onClick={() => !isEditing && handleThreadClick(thread.id)}
                                className="flex-1"
                                tooltip={!isEditing ? thread.title : undefined}
                                disabled={isEditing}
                              >
                                <MessageSquare className="h-4 w-4 shrink-0" />
                                <div className="flex-1 min-w-0">
                                  {isEditing ? (
                                    <input
                                      type="text"
                                      value={editingTitle}
                                      onChange={(e) => setEditingTitle(e.target.value)}
                                      onKeyDown={(e) => handleKeyDown(e, thread.id)}
                                      onBlur={() => handleSaveEdit(thread.id)}
                                      className="w-full px-2 py-1 text-sm bg-background border border-input rounded"
                                      autoFocus
                                      onClick={(e) => e.stopPropagation()}
                                    />
                                  ) : (
                                    <>
                                      <p className="text-sm font-medium truncate">{thread.title}</p>
                                      <p className="text-xs text-muted-foreground">
                                        {formatDistanceToNow(new Date(thread.updatedAt), { addSuffix: true })}
                                      </p>
                                    </>
                                  )}
                                </div>
                              </SidebarMenuButton>
                              {!isEditing && (
                                <div className="flex gap-1 opacity-0 group-hover/thread:opacity-100 transition-opacity">
                                  <button
                                    onClick={(e) => handleStartEdit(e, thread.id, thread.title)}
                                    className="p-2 hover:bg-accent rounded"
                                    aria-label="Rename conversation"
                                  >
                                    <Pencil className="h-3.5 w-3.5" />
                                  </button>
                                  <button
                                    onClick={(e) => handleDeleteThread(e, thread.id)}
                                    className="p-2 hover:bg-destructive/10 rounded"
                                    aria-label="Delete conversation"
                                  >
                                    <Trash2 className="h-3.5 w-3.5 text-destructive" />
                                  </button>
                                </div>
                              )}
                            </div>
                          </SidebarMenuItem>
                        )
                      })
                    )}
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
