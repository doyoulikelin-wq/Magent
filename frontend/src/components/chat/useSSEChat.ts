import { useState } from 'react'

import { getToken } from '../../api/client'

type Message = {
  id: string
  role: 'user' | 'assistant'
  content: string
}

export function useSSEChat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [streaming, setStreaming] = useState(false)
  const [error, setError] = useState('')

  const send = async (text: string) => {
    setError('')
    const userMessage: Message = { id: crypto.randomUUID(), role: 'user', content: text }
    setMessages((prev) => [...prev, userMessage])

    const assistantId = crypto.randomUUID()
    setMessages((prev) => [...prev, { id: assistantId, role: 'assistant', content: '' }])

    setStreaming(true)
    try {
      const apiBase = import.meta.env.VITE_API_BASE_URL ?? ''
      const token = getToken()
      const res = await fetch(`${apiBase}/api/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ message: text }),
      })

      if (!res.ok || !res.body) {
        throw new Error(await res.text())
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { value, done } = await reader.read()
        if (done) {
          break
        }

        buffer += decoder.decode(value, { stream: true })
        const events = buffer.split('\n\n')
        buffer = events.pop() ?? ''

        for (const raw of events) {
          const line = raw
            .split('\n')
            .find((x) => x.startsWith('data:'))
            ?.slice(5)
            .trim()
          if (!line) {
            continue
          }

          const data = JSON.parse(line) as { type: 'token' | 'done'; delta?: string; result?: { answer_markdown: string } }
          if (data.type === 'token' && data.delta) {
            setMessages((prev) =>
              prev.map((m) => (m.id === assistantId ? { ...m, content: `${m.content}${data.delta}` } : m)),
            )
          }
          if (data.type === 'done' && data.result?.answer_markdown) {
            setMessages((prev) =>
              prev.map((m) => (m.id === assistantId ? { ...m, content: data.result!.answer_markdown } : m)),
            )
          }
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '发送失败')
    } finally {
      setStreaming(false)
    }
  }

  return { messages, streaming, error, send }
}
