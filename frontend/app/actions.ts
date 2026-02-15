'use server'

import { revalidateTag } from 'next/cache'

/**
 * Server action to revalidate the threads cache tag.
 * This is used by the client to refresh the sidebar after thread operations.
 */
export async function revalidateThreads() {
  revalidateTag('threads')
}
