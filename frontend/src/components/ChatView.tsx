import { useState } from 'react'
import type { FormEvent } from 'react'

import { sendChatMessage } from '../api/chat'
import type { ChatMessage } from '../types/chat'

const DEFAULT_MODEL = 'qwen2.5:1.5b'

function createMessageId(): string {
  return crypto.randomUUID()
}

export function ChatView() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [message, setMessage] = useState('')
  const [model, setModel] = useState(DEFAULT_MODEL)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const cleanMessage = message.trim()

    if (!cleanMessage || sending) {
      return
    }

    const userMessage: ChatMessage = {
      id: createMessageId(),
      role: 'user',
      content: cleanMessage,
    }

    setMessages((currentMessages) => [
      ...currentMessages,
      userMessage,
    ])

    setMessage('')
    setSending(true)
    setError(null)

    try {
      const response = await sendChatMessage({
        model,
        message: cleanMessage,
      })

      const assistantMessage: ChatMessage = {
        id: createMessageId(),
        role: 'assistant',
        content: response.reply,
        sources: response.sources,
      }

      setMessages((currentMessages) => [
        ...currentMessages,
        assistantMessage,
      ])
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to generate a response.',
      )
    } finally {
      setSending(false)
    }
  }

  function clearConversation() {
    setMessages([])
    setError(null)
  }

  return (
    <>
      <section className="hero">
        <div>
          <p className="eyebrow">Private RAG inference</p>
          <h1>ORMVAO Knowledge Assistant</h1>

          <p className="hero-copy">
            Ask questions against the local knowledge base and receive
            answers grounded in retrieved documentation.
          </p>
        </div>

        <div className="summary-card">
          <span>Architecture</span>
          <strong>RAG + Ollama</strong>
        </div>
      </section>

      <section className="content">
        <div className="chat-toolbar">
          <div>
            <p className="eyebrow">Knowledge assistant</p>
            <h2>Ask the private documentation</h2>
          </div>

          <div className="chat-toolbar-actions">
            <label className="chat-model-field">
              <span>Model</span>

              <select
                value={model}
                onChange={(event) => setModel(event.target.value)}
                disabled={sending}
              >
                <option value="qwen2.5:1.5b">
                  Qwen 2.5 1.5B
                </option>
              </select>
            </label>

            <button
              type="button"
              className="chat-clear-button"
              onClick={clearConversation}
              disabled={messages.length === 0 || sending}
            >
              Clear
            </button>
          </div>
        </div>

        <div className="chat-shell">
          <div
            className="chat-messages"
            aria-live="polite"
            aria-label="Chat messages"
          >
            {messages.length === 0 && (
              <div className="chat-empty-state">
                <div className="chat-empty-icon">RAG</div>

                <h3>Ask the local knowledge base</h3>

                <p>
                  The assistant searches local documentation before
                  generating its answer.
                </p>
              </div>
            )}

            {messages.map((chatMessage) => (
              <div
                key={chatMessage.id}
                className={`chat-message chat-message-${chatMessage.role}`}
              >
                <div className="chat-message-role">
                  {chatMessage.role === 'user'
                    ? 'You'
                    : 'ORMVAO Assistant'}
                </div>

                <div className="chat-message-content">
                  {chatMessage.content}

                  {chatMessage.sources &&
                    chatMessage.sources.length > 0 && (
                      <div className="chat-sources">
                        <strong>Sources</strong>

                        <ul>
                          {chatMessage.sources.map((source) => (
                            <li key={source}>{source}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                </div>
              </div>
            ))}

            {sending && (
              <div className="chat-message chat-message-assistant">
                <div className="chat-message-role">
                  ORMVAO Assistant
                </div>

                <div className="chat-message-content chat-thinking">
                  Searching documentation and generating response...
                </div>
              </div>
            )}
          </div>

          {error && (
            <div className="chat-error" role="alert">
              {error}
            </div>
          )}

          <form
            className="chat-composer"
            onSubmit={handleSubmit}
          >
            <textarea
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              placeholder="Ask a question about the available documentation..."
              rows={3}
              maxLength={10_000}
              disabled={sending}
            />

            <div className="chat-composer-footer">
              <span>
                {message.length.toLocaleString()} / 10,000
              </span>

              <button
                type="submit"
                className="chat-send-button"
                disabled={!message.trim() || sending}
              >
                {sending ? 'Generating...' : 'Send'}
              </button>
            </div>
          </form>
        </div>
      </section>
    </>
  )
}