import DOMPurify from 'dompurify'
import { marked } from 'marked'

type Props = {
  role: 'user' | 'assistant'
  content: string
}

export function MessageBubble({ role, content }: Props) {
  const isUser = role === 'user'
  const html = DOMPurify.sanitize(marked.parse(content, { async: false }) as string)

  return (
    <div className={['flex', isUser ? 'justify-end' : 'justify-start'].join(' ')}>
      <div
        className={[
          'max-w-[90%] rounded-2xl px-4 py-3 text-sm',
          isUser ? 'bg-primary text-white' : 'border border-slate-200 bg-white text-slate-800',
        ].join(' ')}
      >
        <div dangerouslySetInnerHTML={{ __html: html }} />
      </div>
    </div>
  )
}
