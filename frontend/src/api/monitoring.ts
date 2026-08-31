import type { MonitoringDashboard } from '../types/monitoring'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export async function fetchMonitoringDashboard(): Promise<MonitoringDashboard> {
  const response = await fetch(`${API_BASE_URL}/dashboard`)

  if (!response.ok) {
    throw new Error(`Failed to load monitoring data: ${response.status}`)
  }

  return response.json() as Promise<MonitoringDashboard>
}