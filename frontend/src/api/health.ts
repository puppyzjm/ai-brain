import axios from 'axios'

export interface HealthResponse {
  status: string
  database: string
  redis: string
}

export async function fetchHealth(): Promise<HealthResponse> {
  const { data } = await axios.get<HealthResponse>('/health')
  return data
}
