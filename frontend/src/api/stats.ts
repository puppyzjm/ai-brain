import client from './client'

export interface UsageSummary {
  total_requests: number
  success_count: number
  failed_count: number
  success_rate: number
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  avg_latency_ms: number
}

export interface TypeStat {
  type: string
  count: number
  total_tokens: number
}

export interface DailyStat {
  date: string
  count: number
  total_tokens: number
}

export interface UsageStats {
  summary: UsageSummary
  by_type: TypeStat[]
  daily: DailyStat[]
}

export async function fetchUsageStats(): Promise<UsageStats> {
  return (await client.get('/stats/usage')) as unknown as Promise<UsageStats>
}
