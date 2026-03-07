import { z } from 'zod'
import { eventSchemas, type SSEEventName } from './sse-schemas'

/**
 * Parse and validate an SSE event payload with the appropriate Zod schema.
 *
 * @param eventType - The SSE event name (e.g. "token", "citation", "end").
 * @param raw - The raw event object, event.data string, or already-parsed object.
 * @returns The type-safe validated payload, or null if parsing/validation fails.
 */
export function parseSSEEvent<K extends SSEEventName>(
  eventType: K,
  raw: MessageEvent | { data?: string } | string | unknown,
): z.infer<(typeof eventSchemas)[K]> | null {
  try {
    let payload: unknown

    if (typeof raw === 'string') {
      payload = JSON.parse(raw)
    } else if (raw !== null && typeof raw === 'object' && 'data' in raw && typeof (raw as { data?: string }).data === 'string') {
      payload = JSON.parse((raw as { data: string }).data)
    } else {
      payload = raw
    }

    const schema = eventSchemas[eventType]
    const result = schema.safeParse(payload)

    if (!result.success) {
      console.warn(`[SSE] Schema validation failed for "${eventType}" event:`, result.error.format())
      return null
    }

    return result.data as z.infer<(typeof eventSchemas)[K]>
  } catch (err) {
    console.error(`[SSE] Failed to parse "${eventType}" event data:`, err)
    return null
  }
}
