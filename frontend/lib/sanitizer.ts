/**
 * Pass-through sanitizer for auth tokens.
 * Can be enhanced with DOMPurify if token values are ever rendered as HTML.
 * @param token - The raw token string to sanitize.
 * @returns The sanitized token string.
 */
export function sanitizeToken(token: string): string {
  // Simple pass-through for now, can be enhanced with DOMPurify if needed
  return token;
}

/**
 * Type-guard that verifies a citation object has the required shape
 * before it is rendered in the UI.
 * @param citation - An unknown value received from the API.
 * @returns `true` if the value is a safe, well-formed citation object.
 */
export function isCitationSafe(citation: unknown): boolean {
  return (
    !!citation &&
    typeof citation === 'object' &&
    typeof (citation as Record<string, unknown>).chunk_id === 'string' &&
    typeof (citation as Record<string, unknown>).document_title === 'string'
  );
}
