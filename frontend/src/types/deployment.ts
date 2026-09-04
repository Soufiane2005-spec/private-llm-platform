import type { JobStatus } from './job'
import type { LLMEngine } from './model'

export type ModelDeploymentStatus =
  | 'stopped'
  | 'deploying'
  | 'loading'
  | 'running'
  | 'failed'

export interface ModelDeployment {
  deployment_id: string
  model: string
  engine: LLMEngine
  status: ModelDeploymentStatus
  runtime_state: string
  error: string | null
  gpu_available: boolean | null
}

export interface DeploymentJob {
  job_id: string
  status: JobStatus
  error: string | null
}

export interface DeploymentOperation {
  deployment: ModelDeployment | null
  job: DeploymentJob
}
