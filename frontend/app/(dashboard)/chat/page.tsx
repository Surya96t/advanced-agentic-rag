/**
 * Chat page
 * Main interface for conversational RAG
 */

'use client'

import { MessageList } from '@/components/chat/message-list'
import { MessageInput } from '@/components/chat/message-input'
import { Card } from '@/components/ui/card'
import { useChat } from '@/hooks/useChat'

export default function ChatPage() {
  const { messages, isLoading, currentAgent, sendMessage } = useChat()

  return (
    <div className="container mx-auto py-8 px-4 max-w-6xl h-[calc(100vh-8rem)]">
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold mb-2">Chat</h1>
          <p className="text-muted-foreground">
            Ask questions about your API documentation
          </p>
        </div>

        {/* Chat Container */}
        <Card className="flex-1 flex flex-col overflow-hidden">
          {/* Message List */}
          <MessageList 
            messages={messages} 
            currentAgent={currentAgent}
            isLoading={isLoading}
          />

          {/* Message Input */}
          <div className="border-t p-4">
            <MessageInput
              onSend={sendMessage}
              disabled={isLoading}
              placeholder="Ask a question about your documentation..."
            />
          </div>
        </Card>
      </div>
    </div>
  )
}
