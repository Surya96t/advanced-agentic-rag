import { create } from 'zustand'

export interface RateLimitState {
  limit: number | null
  remaining: number | null
  resetTime: number | null // Unix timestamp
  isRateLimited: boolean
  setRateLimit: (limit: number, remaining: number, resetTime: number) => void
  clearRateLimit: () => void
}

export const useRateLimitStore = create<RateLimitState>((set) => ({
  limit: null,
  remaining: null,
  resetTime: null,
  isRateLimited: false,
  setRateLimit: (limit, remaining, resetTime) => {
    console.log('[Rate Limit Store] Setting rate limit:', {
      limit,
      remaining,
      resetTime,
      isRateLimited: remaining === 0,
      resetDate: new Date(resetTime * 1000).toLocaleString()
    })
    set({
      limit,
      remaining,
      resetTime,
      isRateLimited: remaining === 0,
    })
  },
  clearRateLimit: () => {
    console.log('[Rate Limit Store] Clearing rate limit')
    set({
      limit: null,
      remaining: null,
      resetTime: null,
      isRateLimited: false,
    })
  },
}))
