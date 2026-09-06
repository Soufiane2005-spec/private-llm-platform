import type { ModelCatalogEntry, ModelCreatePayload } from '../types/model'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export async function fetchModels(): Promise<ModelCatalogEntry[]> {
  const response = await fetch(`${API_BASE_URL}/models`)

  if (!response.ok) {
    throw new Error(`Failed to load models: ${response.status}`)
  }

  return response.json() as Promise<ModelCatalogEntry[]>
}

export async function createModel(
  token: string,
  payload: ModelCreatePayload,
): Promise<ModelCatalogEntry> {
  const response = await fetch(`${API_BASE_URL}/models`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    throw new Error(await errorMessage(response, 'Failed to create model'))
  }

  return response.json() as Promise<ModelCatalogEntry>
}

export async function updateModel(
  token: string,
  modelId: string,
  payload: Partial<ModelCreatePayload>,
): Promise<ModelCatalogEntry> {
  const response = await fetch(`${API_BASE_URL}/models/${modelId}`, {
    method: 'PATCH',
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    throw new Error(await errorMessage(response, 'Failed to update model'))
  }

  return response.json() as Promise<ModelCatalogEntry>
}

export async function deleteModel(
  token: string,
  modelId: string,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/models/${modelId}`, {
    method: 'DELETE',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (!response.ok) {
    throw new Error(await errorMessage(response, 'Failed to delete model'))
  }
}

function authHeaders(token: string) {
  return {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  }
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
