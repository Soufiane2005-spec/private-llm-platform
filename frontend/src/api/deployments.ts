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
    throw new Error(await errorMessage(response, 'Deployment operation failed'))
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

export async function deleteDeployment(
  token: string,
  deploymentId: string,
): Promise<DeploymentOperation> {
  const response = await fetch(`${API_BASE_URL}/deployments/${deploymentId}`, {
    method: 'DELETE',
    headers: authHeaders(token),
  })

  return parseOperation(response)
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
