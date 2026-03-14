export interface SSEClientConfig {
  url: string
  method?: string
  headers?: Record<string, string>
  body?: unknown
  maxRetries?: number
  baseDelay?: number
  maxDelay?: number
  signal?: AbortSignal
  onHeaders?: (headers: Headers) => void
  onEvent?: (event: SSEEvent) => void
  onError?: (error: Error, retryCount: number) => void
  onReconnect?: (retryCount: number) => void
  onOpen?: () => void
}

export interface SSEEvent {
  event: string
  data: string
  id?: string
}

export interface SSEMetrics {
  startTime: number | null
  endTime: number | null
  duration: number | null
  totalBytes: number
  eventCount: number
}

export class SSEClient {
  private config: Required<Pick<SSEClientConfig, 'method' | 'headers' | 'maxRetries' | 'baseDelay' | 'maxDelay'>> & Omit<SSEClientConfig, 'method' | 'headers' | 'maxRetries' | 'baseDelay' | 'maxDelay'>
  private retryCount = 0
  private controller: AbortController | null = null
  private isConnecting = false
  private metrics: SSEMetrics = {
    startTime: null,
    endTime: null,
    duration: null,
    totalBytes: 0,
    eventCount: 0,
  }

  constructor(config: SSEClientConfig) {
    this.config = {
      method: 'POST',
      headers: {},
      maxRetries: 3,
      baseDelay: 1000,
      maxDelay: 10000,
      ...config,
    }
  }

  public async connect(): Promise<void> {
    if (this.isConnecting) return
    this.isConnecting = true
    this.metrics = {
      startTime: Date.now(),
      endTime: null,
      duration: null,
      totalBytes: 0,
      eventCount: 0,
    }

    try {
      await this.connectWithRetry()
    } finally {
      this.isConnecting = false
      this.metrics.endTime = Date.now()
      this.metrics.duration = this.metrics.endTime - (this.metrics.startTime || 0)
    }
  }

  public cancel(): void {
    if (this.controller) {
      this.controller.abort()
      this.controller = null
    }
  }

  public getMetrics(): SSEMetrics {
    const currentEndTime = this.metrics.endTime || Date.now()
    const currentDuration = currentEndTime - (this.metrics.startTime || 0)
    return {
      ...this.metrics,
      endTime: currentEndTime,
      duration: currentDuration,
    }
  }

  private async connectWithRetry(): Promise<void> {
    try {
      if (this.config.signal?.aborted) {
        return
      }

      this.controller = new AbortController()
      
      // Combine external signal with internal controller
      if (this.config.signal) {
        this.config.signal.addEventListener('abort', () => {
          this.controller?.abort()
        })
      }

      const response = await fetch(this.config.url, {
        method: this.config.method,
        headers: {
          'Accept': 'text/event-stream',
          ...this.config.headers,
        },
        body: this.config.body ? JSON.stringify(this.config.body) : undefined,
        signal: this.controller.signal,
      })

      if (!response.ok) {
        if (response.status >= 400 && response.status < 500 && response.status !== 429) {
          throw new Error(`SSE Fatal Error: ${response.status} ${response.statusText}`)
        }
        throw new Error(`SSE connection failed: ${response.statusText}`)
      }

      if (this.config.onHeaders) {
        this.config.onHeaders(response.headers)
      }
      
      if (this.config.onOpen) {
        this.config.onOpen()
      }

      this.retryCount = 0

      if (!response.body) {
        throw new Error('No response body')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let currentEvent: Partial<SSEEvent> = {}

      while (true) {
        const { done, value } = await reader.read()

        if (done) {
          break
        }

        this.metrics.totalBytes += value.length
        const chunk = decoder.decode(value, { stream: true })
        buffer += chunk
        
        const lines = buffer.split('\n')
        // Keep the last partial line in buffer
        buffer = lines.pop() || ''

        for (const line of lines) {
          const trimmedLine = line.trim()
          
          if (trimmedLine === '') {
            // Empty line means end of event block
            if (currentEvent.data) {
              this.metrics.eventCount++
              if (this.config.onEvent) {
                this.config.onEvent({
                  event: currentEvent.event || 'message',
                  data: currentEvent.data,
                  id: currentEvent.id
                })
              }
              // Reset for next event
              currentEvent = {}
            }
            continue
          }

          if (trimmedLine.startsWith('event:')) {
            currentEvent.event = trimmedLine.slice(6).trim()
          } else if (trimmedLine.startsWith('data:')) {
            const data = trimmedLine.slice(5).trim()
            if (currentEvent.data) {
              currentEvent.data += '\n' + data
            } else {
              currentEvent.data = data
            }
          } else if (trimmedLine.startsWith('id:')) {
            currentEvent.id = trimmedLine.slice(3).trim()
          }
        }
      }
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        return
      }

      if (this.retryCount < this.config.maxRetries) {
        this.retryCount++
        const delay = Math.min(
          this.config.baseDelay * Math.pow(2, this.retryCount - 1),
          this.config.maxDelay
        )
        
        console.log(`SSE connection failed, retrying in ${delay}ms... (Attempt ${this.retryCount})`)
        
        if (this.config.onReconnect) {
          this.config.onReconnect(this.retryCount)
        }

        await new Promise((resolve) => setTimeout(resolve, delay))
        return this.connectWithRetry()
      }

      if (this.config.onError) {
        this.config.onError(error instanceof Error ? error : new Error(String(error)), this.retryCount)
      }
      throw error
    }
  }
}
