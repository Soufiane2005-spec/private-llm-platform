import type { Job, JobRunResult, JobRuntime } from '../types/job'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export async function fetchJobs(): Promise<Job[]> {
  const response = await fetch(`${API_BASE_URL}/jobs`)

  if (!response.ok) {
    throw new Error(`Failed to load jobs: ${response.status}`)
  }

  return response.json() as Promise<Job[]>
}

export async function fetchJobRuntime(): Promise<JobRuntime> {
  const response = await fetch(`${API_BASE_URL}/jobs/runtime`)

  if (!response.ok) {
    throw new Error(`Failed to load job runtime: ${response.status}`)
  }

  return response.json() as Promise<JobRuntime>
}

export async function fetchDeadLetterJobs(): Promise<Job[]> {
  const response = await fetch(`${API_BASE_URL}/jobs/dead-letter`)

  if (!response.ok) {
    throw new Error(`Failed to load dead-letter jobs: ${response.status}`)
  }

  return response.json() as Promise<Job[]>
}

export async function runNextJob(): Promise<JobRunResult> {
  const response = await fetch(`${API_BASE_URL}/jobs/run-next`, {
    method: 'POST',
  })

  if (!response.ok) {
    throw new Error(`Failed to run next job: ${response.status}`)
  }

  return response.json() as Promise<JobRunResult>
}
