/**
 * Chat page (no thread selected)
 * Shows empty state prompting user to select or create a conversation
 * Individual threads are at /chat/[threadId]
 */

'use client'

import { useEffect } from 'react'
import { MessageSquare } from 'lucide-react'
import { useChatStore } from '@/stores/chat-store'

export default function ChatPage() {
  const { clearMessages, setCurrentThreadId } = useChatStore()
  
  // Clear messages when landing on /chat (no thread selected)
  useEffect(() => {
    console.log('[ChatPage] Clearing messages - no thread selected')
    clearMessages()
    setCurrentThreadId(null)
  }, [clearMessages, setCurrentThreadId])

  return (
    <div className="flex flex-1 items-center justify-center">
      <div className="flex flex-col items-center gap-4 text-center">
        <div className="rounded-full bg-muted p-6">
          <MessageSquare className="h-12 w-12 text-muted-foreground" />
        </div>
        <div className="space-y-2">
          <h2 className="text-2xl font-semibold tracking-tight">
            No conversation selected
          </h2>
          <p className="text-sm text-muted-foreground max-w-sm">
            Select a conversation from the sidebar or start a new one to begin chatting
          </p>
        </div>
      </div>
    </div>
  )
}
