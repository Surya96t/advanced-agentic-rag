/**
 * SWR-based thread history hook
 *
 * Replaces the Zustand loadThreads() + full-array-replacement pattern with a
 * targeted SWR cache entry. Any component that calls useThreadHistory() stays
 * subscribed to the same cache key and re-renders only when that key changes.
 *
 * Call mutateThreadHistory() from anywhere (hook, store action, event handler)
 * to trigger a surgical re-fetch without touching unrelated state.
 */

'use client'

import useSWR, { mutate } from 'swr'
import { revalidateThreads } from '@/app/actions'
import type { Thread } from '@/stores/chat-store'

export const THREADS_SWR_KEY = '/api/threads'

type RawThread = {
  thread_id: string
  title: string
  preview?: string
  message_count: number
  created_at: string
  updated_at: string
  user_id: string
}

async function fetchThreads(_key: string): Promise<Thread[]> {
  const response = await fetch(_key, { credentials: 'include' })
  if (!response.ok) throw new Error('Failed to load threads')
  const raw: RawThread[] = await response.json()
  return raw.map((t) => ({
    id: t.thread_id,
    title: t.title,
    preview: t.preview,
    messageCount: t.message_count,
    createdAt: new Date(t.created_at),
    updatedAt: new Date(t.updated_at),
    userId: t.user_id,
  }))
}

/**
 * Hook for the sidebar thread list.
 * The first component to mount with this hook triggers the initial fetch;
 * subsequent mounts share the cached result without extra network requests.
 */
export function useThreadHistory() {
  const { data, error, isLoading } = useSWR(THREADS_SWR_KEY, fetchThreads, {
    revalidateOnFocus: false,
    dedupingInterval: 5000,
  })

  return {
    threads: data ?? [],
    isLoadingThreads: isLoading,
    error: error as Error | undefined,
  }
}

/**
 * Invalidates the Next.js server-side data cache for the threads route, then
 * triggers a targeted SWR re-fetch. Safe to call from any hook, component, or
 * event handler.
 *
 * This replaces the previous revalidateThreads() + loadThreads() waterfall
 * with a single surgical cache update — only the changed sidebar entry
 * re-renders, with no loading spinner or full-list replacement.
 */
export async function mutateThreadHistory(): Promise<void> {
  // Invalidate the Next.js fetch cache tag first so the route handler
  // returns fresh data from the backend on the next request.
  await revalidateThreads()
  // Then tell SWR to re-fetch, which now bypasses the server cache.
  await mutate(THREADS_SWR_KEY)
}

/**
 * Optimistically prepend a new placeholder thread to the SWR cache without
 * triggering a network re-fetch. The entry is replaced by the real DB row
 * when the next revalidation fires (triggered by mutateThreadHistory() or
 * the thread_title event handler).
 */
export function insertThreadOptimistically(thread: Thread): void {
  mutate(
    THREADS_SWR_KEY,
    (current: Thread[] | undefined) => [thread, ...(current ?? [])],
    { revalidate: false },
  )
}

/**
 * Optimistically update the title of a thread in the SWR cache without
 * triggering a network re-fetch. Used when the backend streams a
 * `thread_title` event so the sidebar reflects the new title immediately.
 */
export function updateThreadTitleOptimistically(threadId: string, title: string): void {
  mutate(
    THREADS_SWR_KEY,
    (current: Thread[] | undefined) =>
      (current ?? []).map((t) => (t.id === threadId ? { ...t, title } : t)),
    { revalidate: false },
  )
}
