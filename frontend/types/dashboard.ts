/**
 * Dashboard statistics types
 */
export interface DashboardStats {
  documents_count: number
  chunks_count: number
  conversations_count: number
  queries_count: number
  total_tokens: number
  total_cost: number
  avg_latency_seconds: number
  error_rate: number
}
