/**
 * Chat page
 * Main interface for conversational RAG
 */

'use client'

import { MessageList } from '@/components/chat/message-list'
import { MessageInput } from '@/components/chat/message-input'
import { ChatEmptyState } from '@/components/chat/chat-empty-state'
import { RateLimitBanner } from '@/components/rate-limit-banner'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { StopCircle } from 'lucide-react'
import { useChat } from '@/hooks/useChat'
import { useRateLimitStore } from '@/stores/rate-limit-store'

export default function ChatPage() {
  const { messages, isLoading, currentAgent, sendMessage, cancelStream } = useChat()
  const { isRateLimited } = useRateLimitStore()

  const hasMessages = messages.length > 0

  return (
    <>
      {/* Rate Limit Banner */}
      <RateLimitBanner />
      
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
            {/* Message List or Empty State */}
            {hasMessages ? (
              <MessageList 
                messages={messages} 
                currentAgent={currentAgent}
                isLoading={isLoading}
              />
            ) : (
              <ChatEmptyState />
            )}

            {/* Message Input */}
            <div className="border-t p-4">
              <div className="flex gap-2 items-end">
                <div className="flex-1">
                  <MessageInput
                    onSend={sendMessage}
                    disabled={isLoading || isRateLimited}
                    placeholder={
                      isRateLimited
                        ? "Rate limit exceeded. Please wait..."
                        : "Ask a question about your documentation..."
                    }
                  />
                </div>
                {isLoading && (
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={cancelStream}
                    title="Stop generation"
                    className="shrink-0"
                  >
                    <StopCircle className="h-4 w-4" />
                  </Button>
                )}
              </div>
            </div>
          </Card>
        </div>
      </div>
    </>
  )
}
