/**
 * Thread Sidebar Component
 * Displays list of conversation threads with create/delete actions
 */

'use client'

import { useEffect } from 'react'
import { useChatStore } from '@/stores/chat-store'
import { formatDistanceToNow } from 'date-fns'
import { Plus, Trash2, MessageSquare, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'

export function ThreadSidebar() {
  const {
    threads,
    currentThreadId,
    isLoadingThreads,
    loadThreads,
    createNewThread,
    loadThread,
    deleteThread,
  } = useChatStore()

  // Load threads on mount (only once, not on store changes)
  useEffect(() => {
    loadThreads()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Empty deps - load only on mount

  const handleNewChat = async () => {
    try {
      await createNewThread()
    } catch (error) {
      console.error('Failed to create new thread:', error)
      toast.error('Failed to create chat', {
        description: error instanceof Error ? error.message : 'An unexpected error occurred'
      })
    }
  }

  return (
    <div className="w-64 border-r bg-muted/10 flex flex-col h-full">
      {/* Header with New Chat button */}
      <div className="p-4 border-b">
        <button
          onClick={handleNewChat}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors font-medium text-sm"
        >
          <Plus className="w-4 h-4" />
          New Chat
        </button>
      </div>

      {/* Thread list */}
      <div className="flex-1 overflow-y-auto p-2">
        {isLoadingThreads ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
          </div>
        ) : threads.length === 0 ? (
          <div className="text-center text-muted-foreground py-8 px-4">
            <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No conversations yet</p>
            <p className="text-xs mt-1 opacity-75">Start a new chat to get started</p>
          </div>
        ) : (
          <div className="space-y-1">
            {threads.map((thread) => (
              <ThreadItem
                key={thread.id}
                thread={thread}
                isActive={thread.id === currentThreadId}
                onSelect={() => loadThread(thread.id)}
                onDelete={() => deleteThread(thread.id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

interface ThreadItemProps {
  thread: {
    id: string
    title: string
    preview?: string
    messageCount: number
    updatedAt: Date
  }
  isActive: boolean
  onSelect: () => void
  onDelete: () => void
}

function ThreadItem({ thread, isActive, onSelect, onDelete }: ThreadItemProps) {
  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation()
    
    // Confirm deletion
    if (window.confirm(`Delete conversation "${thread.title}"?`)) {
      onDelete()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Activate on Enter or Space
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      onSelect()
    }
  }

  return (
    <div
      role="button"
      tabIndex={0}
      aria-pressed={isActive}
      aria-label={`Conversation: ${thread.title}, ${thread.messageCount} messages, updated ${formatDistanceToNow(new Date(thread.updatedAt), { addSuffix: true })}`}
      className={cn(
        "group p-3 rounded-lg cursor-pointer transition-all duration-200",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        isActive 
          ? "bg-accent border border-accent-foreground/10 shadow-sm" 
          : "hover:bg-accent/50 border border-transparent"
      )}
      onClick={onSelect}
      onKeyDown={handleKeyDown}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          {/* Thread title with icon */}
          <div className="flex items-center gap-2 mb-1">
            <MessageSquare className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
            <p className="font-medium text-sm truncate">
              {thread.title}
            </p>
          </div>
          
          {/* Preview text */}
          {thread.preview && (
            <p className="text-xs text-muted-foreground truncate mb-1 pl-5">
              {thread.preview}
            </p>
          )}
          
          {/* Metadata */}
          <div className="flex items-center gap-2 text-xs text-muted-foreground pl-5">
            <span>
              {formatDistanceToNow(new Date(thread.updatedAt), { addSuffix: true })}
            </span>
            <span>•</span>
            <span>{thread.messageCount} messages</span>
          </div>
        </div>
        
        {/* Delete button - shows on hover */}
        <button
          onClick={handleDelete}
          className="opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 focus:opacity-100 p-1.5 hover:bg-destructive/10 rounded transition-opacity shrink-0"
          aria-label="Delete conversation"
        >
          <Trash2 className="w-3.5 h-3.5 text-destructive" />
        </button>
      </div>
    </div>
  )
}
