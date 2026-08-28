export type JobStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface Job {
  job_id: string
  job_type: string
  status: JobStatus
  error: string | null
  attempts: number
  max_attempts: number
}