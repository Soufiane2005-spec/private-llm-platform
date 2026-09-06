export type LLMEngine = 'ollama' | 'vllm'

export interface ModelCatalogEntry {
  model_id: string
  display_name: string
  engine: LLMEngine
  engine_model_id: string
  context_length: number | null
  enabled: boolean
  served_model_name: string | null
  gpu_required: boolean
  runtime_available: boolean
  benchmark_model_id: string
}

export interface ModelCreatePayload {
  display_name: string
  engine: LLMEngine
  engine_model_id: string
  context_length: number | null
  enabled: boolean
  served_model_name: string | null
  gpu_required: boolean
}
