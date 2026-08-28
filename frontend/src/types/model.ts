export type LLMEngine = 'ollama' | 'vllm'

export interface ModelCatalogEntry {
  model_id: string
  display_name: string
  engine: LLMEngine
  engine_model_id: string
  context_length: number | null
  enabled: boolean
}