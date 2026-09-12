export interface ChatRequest {
  message: string
  model: string
}

export interface ChatSource {
  source: string
  content: string
  score: number
  chunk_index: number | null
  page: number | null
}

export interface ChatResponse {
  model: string
  reply: string
  sources: ChatSource[]
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: ChatSource[]
}