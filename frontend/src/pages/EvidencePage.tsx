import { useAgentActions } from '../api/hooks'
import { EvidenceDrawer } from '../components/agent/EvidenceDrawer'

export function EvidencePage() {
  const { data: actions, isLoading, error } = useAgentActions()

  // 过滤: status=invalid 隐藏
  const visible = (actions ?? []).filter((a) => a.status !== 'invalid')

  if (isLoading) {
    return (
      <div className="grid animate-pulse gap-4">
        <div className="h-16 rounded-2xl bg-slate-200" />
        <div className="h-16 rounded-2xl bg-slate-200" />
        <div className="h-16 rounded-2xl bg-slate-200" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center">
        <div className="text-4xl">🔍</div>
        <h3 className="mt-3 font-heading text-lg font-semibold text-slate-700">暂无证据记录</h3>
        <p className="mt-1 text-sm text-slate-500">
          当代理产生建议和动作后，所有证据链路将在这里展示。
        </p>
      </div>
    )
  }

  return (
    <div className="grid gap-4">
      <div className="text-sm text-slate-500">
        共 {visible.length} 条可追溯的动作记录
      </div>
      <EvidenceDrawer actions={visible} />
    </div>
  )
}
