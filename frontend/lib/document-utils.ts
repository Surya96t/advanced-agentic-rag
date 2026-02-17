
export interface Document {
  id: string;
  created_at: string;
  filename: string;
  file_size: number;
  mime_type: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  user_id: string;
  error?: string;
  summary?: string;
  chunk_count?: number;
}

export type SortField = 'date' | 'name' | 'size';
export type SortOrder = 'asc' | 'desc';

export function formatDate(dateString: string): string {
  if (!dateString) return '';
  const date = new Date(dateString);
  if (isNaN(date.getTime())) return dateString;
  
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: 'numeric',
  }).format(date);
}

export function getFileExtension(filename: string): string {
  if (!filename) return '';
  return filename.split('.').pop()?.toLowerCase() || '';
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

export function generateFileId(): string {
  return Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
}

export function validateFile(file: File): { valid: boolean; error?: string } {
  const MAX_SIZE = 10 * 1024 * 1024; // 10MB
  const ALLOWED_TYPES = [
    'application/pdf',
    'text/plain',
    'text/markdown',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  ];

  if (file.size > MAX_SIZE) {
    return { valid: false, error: 'File size must be less than 10MB' };
  }

  if (!ALLOWED_TYPES.includes(file.type) && !file.name.endsWith('.md')) { // minimal extension check fallback
    return { valid: false, error: 'Invalid file type. Allowed: PDF, TXT, MD, DOCX' };
  }

  return { valid: true };
}

export function searchDocuments(documents: Document[], query: string): Document[] {
  if (!query) return documents;
  const lowerQuery = query.toLowerCase();
  return documents.filter((doc) => 
    doc.filename.toLowerCase().includes(lowerQuery) || 
    (doc.summary && doc.summary.toLowerCase().includes(lowerQuery))
  );
}

export function sortDocuments(documents: Document[], field: SortField, order: SortOrder): Document[] {
  return [...documents].sort((a, b) => {
    let comparison = 0;
    switch (field) {
      case 'date':
        comparison = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
        break;
      case 'name':
        comparison = a.filename.localeCompare(b.filename);
        break;
      case 'size':
        comparison = a.file_size - b.file_size;
        break;
    }
    return order === 'asc' ? comparison : -comparison;
  });
}
