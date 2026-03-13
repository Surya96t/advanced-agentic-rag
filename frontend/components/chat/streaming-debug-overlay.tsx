/**
 * Dev-only streaming performance overlay.
 *
 * Rendered ONLY when process.env.NODE_ENV === 'development'.
 * Hidden when no tokens have been received yet.
 * Fixed to the bottom-right corner — does not affect layout.
 */

'use client'

import type { StreamingMetrics } from '@/stores/chat-store'
import { useStreamingMetrics } from '@/hooks/useStreamingMetrics'

interface StreamingDebugOverlayProps {
  streamingMetrics: StreamingMetrics
}

function fmt(value: number | null, unit: string, decimals = 0): string {
  if (value === null) return '—'
  return `${value.toFixed(decimals)}${unit}`
}

/**
 * Renders a fixed-position debug overlay displaying live streaming performance
 * metrics during development.
 *
 * The hook is always called unconditionally (Rules of Hooks); the overlay is
 * hidden in production and before any tokens have been received.
 *
 * @param props.streamingMetrics - Live metrics snapshot from the chat store.
 * @returns A fixed overlay element in development, or `null` in production /
 *   before streaming begins.
 */
export function StreamingDebugOverlay({ streamingMetrics }: StreamingDebugOverlayProps) {
  // Hook must be called unconditionally on every render (Rules of Hooks)
  const { ttft, tps, tokenCount, p50, p95, p99 } = useStreamingMetrics(streamingMetrics)

  // Strip entirely from production builds
  if (process.env.NODE_ENV !== 'development') return null

  // Hide until streaming has actually started
  if (tokenCount === 0) return null

  return (
    <div
      className="fixed bottom-20 right-4 z-50 rounded-lg border border-border/60 bg-background/90 px-3 py-2 text-xs font-mono shadow-lg backdrop-blur-sm"
      aria-hidden="true"
    >
      <p className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
        Stream metrics
      </p>
      <table className="border-separate border-spacing-x-3">
        <tbody>
          <tr>
            <td className="text-muted-foreground">TTFT</td>
            <td className="text-right tabular-nums">{fmt(ttft, ' ms')}</td>
          </tr>
          <tr>
            <td className="text-muted-foreground">TPS</td>
            <td className="text-right tabular-nums">{fmt(tps, ' t/s', 1)}</td>
          </tr>
          <tr>
            <td className="text-muted-foreground">Tokens</td>
            <td className="text-right tabular-nums">{tokenCount}</td>
          </tr>
          <tr>
            <td className="text-muted-foreground">p50</td>
            <td className="text-right tabular-nums">{fmt(p50, ' ms')}</td>
          </tr>
          <tr>
            <td className="text-muted-foreground">p95</td>
            <td className="text-right tabular-nums">{fmt(p95, ' ms')}</td>
          </tr>
          <tr>
            <td className="text-muted-foreground">p99</td>
            <td className="text-right tabular-nums">{fmt(p99, ' ms')}</td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}
