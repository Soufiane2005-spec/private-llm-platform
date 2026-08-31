import type {
  BenchmarkRecord,
  BenchmarkReport,
} from '../types/benchmark'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export async function fetchBenchmarks(): Promise<BenchmarkRecord[]> {
  const response = await fetch(`${API_BASE_URL}/benchmarks`)

  if (!response.ok) {
    throw new Error(`Failed to load benchmarks: ${response.status}`)
  }

  return response.json() as Promise<BenchmarkRecord[]>
}

export async function fetchBenchmarkReport(): Promise<BenchmarkReport | null> {
  const response = await fetch(`${API_BASE_URL}/benchmarks/report`)

  if (!response.ok) {
    throw new Error(`Failed to load benchmark report: ${response.status}`)
  }

  return response.json() as Promise<BenchmarkReport | null>
}