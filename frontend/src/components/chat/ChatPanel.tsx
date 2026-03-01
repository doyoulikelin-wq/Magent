import { FormEvent, useState } from 'react'

import { MessageBubble } from './MessageBubble'
import { useSSEChat } from './useSSEChat'

export function ChatPanel() {
  const [input, setInput] = useState('')
  const { messages, streaming, error, send } = useSSEChat()

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    const text = input.trim()
    if (!text || streaming) {
      return
    }
    setInput('')
    await send(text)
  }

  return (
    <div className="grid gap-4">
      <div className="h-[56vh] space-y-3 overflow-y-auto rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
        {messages.map((m) => (
          <MessageBubble key={m.id} role={m.role} content={m.content} />
        ))}
        {messages.length === 0 ? <div className="text-sm text-slate-500">输入问题开始聊天，例如：我今天血糖为什么波动大？</div> : null}
      </div>

      <form onSubmit={onSubmit} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          className="h-28 w-full resize-none rounded-lg border border-slate-300 px-3 py-2"
          placeholder="请输入你的问题..."
        />
        <div className="mt-3 flex items-center justify-between">
          <div className="text-sm text-red-600">{error}</div>
          <button
            type="submit"
            disabled={streaming}
            className="rounded-lg bg-primary px-4 py-2 text-white disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {streaming ? '生成中...' : '发送'}
          </button>
        </div>
      </form>
    </div>
  )
}
