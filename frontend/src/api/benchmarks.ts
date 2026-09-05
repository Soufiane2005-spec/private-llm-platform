import type {
  BenchmarkRecord,
  BenchmarkReport,
  BenchmarkRunResponse,
} from '../types/benchmark'
import type { LLMEngine } from '../types/model'
import type { Job } from '../types/job'

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

export async function runBenchmark(
  token: string,
  model: string,
  engine: LLMEngine,
  prompts: string[],
): Promise<BenchmarkRunResponse> {
  const response = await fetch(`${API_BASE_URL}/benchmarks`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ model, engine, prompts }),
  })

  if (!response.ok) {
    throw new Error(await errorMessage(response, 'Failed to run benchmark'))
  }

  return response.json() as Promise<BenchmarkRunResponse>
}

export async function fetchBenchmarkJob(jobId: string): Promise<Job> {
  const response = await fetch(`${API_BASE_URL}/jobs/${jobId}`)

  if (!response.ok) {
    throw new Error(await errorMessage(response, 'Failed to load benchmark job'))
  }

  return response.json() as Promise<Job>
}

async function errorMessage(
  response: Response,
  fallback: string,
): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string }

    if (body.detail) {
      return body.detail
    }
  } catch {
    // Keep the fallback when the API does not return a JSON error body.
  }

  return `${fallback}: ${response.status}`
}
