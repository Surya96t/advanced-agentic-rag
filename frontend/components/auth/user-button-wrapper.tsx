/**
 * Client-side wrapper for Clerk UserButton
 * Prevents hydration errors by rendering only on client
 */

'use client'

import dynamic from 'next/dynamic'

// Dynamically import UserButton with no SSR to prevent hydration issues
const ClientOnlyUserButton = dynamic(
  () => import('@clerk/nextjs').then((mod) => mod.UserButton),
  { 
    ssr: false,
    loading: () => <div className="h-8 w-8" />
  }
)

export function UserButtonWrapper() {
  return <ClientOnlyUserButton afterSignOutUrl="/" />
}
