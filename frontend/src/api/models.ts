import type { ModelCatalogEntry } from '../types/model'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export async function fetchModels(): Promise<ModelCatalogEntry[]> {
  const response = await fetch(`${API_BASE_URL}/models`)

  if (!response.ok) {
    throw new Error(`Failed to load models: ${response.status}`)
  }

  return response.json() as Promise<ModelCatalogEntry[]>
}