import type { ChatRequest, ChatResponse } from '../types/chat'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export async function sendChatMessage(
  request: ChatRequest,
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    let detail = `Chat request failed: ${response.status}`

    try {
      const body = (await response.json()) as { detail?: string }

      if (body.detail) {
        detail = body.detail
      }
    } catch {
      // Keep the fallback error message.
    }

    throw new Error(detail)
  }

  return response.json() as Promise<ChatResponse>
}