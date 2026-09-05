export interface ChatRequest {
  message: string
  model: string
}

export interface ChatResponse {
  model: string
  reply: string
  sources: string[]
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: string[]
}