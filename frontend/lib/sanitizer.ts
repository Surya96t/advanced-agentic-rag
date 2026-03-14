export function sanitizeToken(token: string): string {
  // Simple pass-through for now, can be enhanced with DOMPurify if needed
  return token;
}

export function isCitationSafe(citation: unknown): boolean {
  return (
    citation &&
    typeof citation === 'object' &&
    typeof citation.chunk_id === 'string' &&
    typeof citation.document_title === 'string'
  );
}
