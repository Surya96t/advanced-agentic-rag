/**
 * Derives p50/p95/p99 latency percentiles and other streaming performance stats
 * from the raw inter-token latency array stored in the chat store.
 *
 * Pure computation — no side effects, no store writes.
 */

import { useMemo } from 'react'
import type { StreamingMetrics } from '@/stores/chat-store'

export interface DerivedStreamingMetrics {
  /** Time from sendMessage to first token (ms), or null if not yet received */
  ttft: number | null
  /** Tokens per second (rolling average) */
  tps: number
  /** Total tokens received */
  tokenCount: number
  /** 50th percentile inter-token latency in ms, or null if < 2 tokens */
  p50: number | null
  /** 95th percentile inter-token latency in ms, or null if < 2 tokens */
  p95: number | null
  /** 99th percentile inter-token latency in ms, or null if < 2 tokens */
  p99: number | null
}

function percentile(sorted: number[], p: number): number {
  if (sorted.length === 0) return 0
  const idx = Math.ceil((p / 100) * sorted.length) - 1
  return sorted[Math.max(0, Math.min(idx, sorted.length - 1))]
}

export function useStreamingMetrics(
  metrics: StreamingMetrics,
): DerivedStreamingMetrics {
  return useMemo(() => {
    const { interTokenLatencies, timeToFirstToken, tokensPerSecond, tokenCount } = metrics

    if (interTokenLatencies.length < 2) {
      return {
        ttft: timeToFirstToken,
        tps: tokensPerSecond,
        tokenCount,
        p50: null,
        p95: null,
        p99: null,
      }
    }

    const sorted = [...interTokenLatencies].sort((a, b) => a - b)
    return {
      ttft: timeToFirstToken,
      tps: tokensPerSecond,
      tokenCount,
      p50: percentile(sorted, 50),
      p95: percentile(sorted, 95),
      p99: percentile(sorted, 99),
    }
  }, [metrics])
}
