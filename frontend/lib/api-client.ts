import { auth } from '@clerk/nextjs/server';

const BASE_URL = process.env.FASTAPI_BASE_URL || 'http://localhost:8000';

export async function apiFetch(endpoint: string, options: RequestInit = {}): Promise<Response> {
  const { getToken } = await auth();
  const token = await getToken();

  if (!token) {
    console.warn('No auth token found for apiFetch to', endpoint);
  }

  // Remove leading slash if present in endpoint
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const url = `${BASE_URL}${cleanEndpoint}`;
  
  // Don't set Content-Type for FormData — the browser/Node sets it automatically
  // with the correct multipart boundary. Overriding it breaks file uploads.
  const isFormData = options.body instanceof FormData;
  const headers: Record<string, string> = {
    ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  return fetch(url, {
    ...options,
    headers,
  });
}

/**
 * Helper to fetch and parse JSON
 */
export async function apiJSON<T = any>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const response = await apiFetch(endpoint, options);
  
  if (!response.ok) {
    throw new Error(`API Error: ${response.status} ${response.statusText}`);
  }
  
  return response.json();
}
