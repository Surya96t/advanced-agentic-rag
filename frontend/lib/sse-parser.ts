export function parseEventData<T = any>(event: MessageEvent | any): T | null {
  try {
    if (typeof event === 'string') {
      return JSON.parse(event);
    }
    if (event?.data) {
      return JSON.parse(event.data);
    }
    return event as T;
  } catch (error) {
    console.error('Failed to parse SSE event data', error);
    return null;
  }
}
