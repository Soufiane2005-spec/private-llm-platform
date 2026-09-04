import type {
  DeploymentOperation,
  ModelDeployment,
} from '../types/deployment'
import type { LLMEngine } from '../types/model'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

function authHeaders(token: string) {
  return {
    Authorization: `Bearer ${token}`,
  }
}

async function parseOperation(response: Response): Promise<DeploymentOperation> {
  if (!response.ok) {
    throw new Error(`Deployment operation failed: ${response.status}`)
  }

  return response.json() as Promise<DeploymentOperation>
}

export async function fetchDeployments(
  token: string,
): Promise<ModelDeployment[]> {
  const response = await fetch(`${API_BASE_URL}/deployments`, {
    headers: authHeaders(token),
  })

  if (!response.ok) {
    throw new Error(`Failed to load deployments: ${response.status}`)
  }

  return response.json() as Promise<ModelDeployment[]>
}

export async function deployModel(
  token: string,
  model: string,
  engine: LLMEngine,
): Promise<DeploymentOperation> {
  const response = await fetch(`${API_BASE_URL}/deployments`, {
    method: 'POST',
    headers: {
      ...authHeaders(token),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ model, engine }),
  })

  return parseOperation(response)
}

export async function runDeploymentAction(
  token: string,
  deploymentId: string,
  action: 'start' | 'stop' | 'restart',
): Promise<DeploymentOperation> {
  const response = await fetch(
    `${API_BASE_URL}/deployments/${deploymentId}/${action}`,
    {
      method: 'POST',
      headers: authHeaders(token),
    },
  )

  return parseOperation(response)
}
