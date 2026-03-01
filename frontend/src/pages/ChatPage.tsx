import { ChatPanel } from '../components/chat/ChatPanel'

export function ChatPage() {
  return (
    <div className="grid gap-4">
      <div className="rounded-2xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
        仅提供健康信息与生活方式建议，不替代医疗诊断或处方建议。
      </div>
      <ChatPanel />
    </div>
  )
}
