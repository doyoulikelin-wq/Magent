import { useAgentActions, useSubmitFeedback } from '../api/hooks'
import type { RescueAction as RescueActionType } from '../api/types'
import { RescueActionCard } from '../components/agent/RescueActionCard'

export function RescuePage() {
  const { data: actions, isLoading, error } = useAgentActions('rescue')
  const feedback = useSubmitFeedback()

  // 过滤: status=invalid 隐藏
  const visible = (actions ?? []).filter(
    (a): a is RescueActionType => a.action_type === 'rescue' && a.status !== 'invalid',
  )

  function handleFeedback(actionId: string, choice: 'executed' | 'not_executed' | 'partial') {
    feedback.mutate({ action_id: actionId, user_feedback: choice })
  }

  if (isLoading) {
    return (
      <div className="grid animate-pulse gap-4">
        <div className="h-48 rounded-2xl bg-slate-200" />
        <div className="h-48 rounded-2xl bg-slate-200" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center">
        <div className="text-4xl">🚑</div>
        <h3 className="mt-3 font-heading text-lg font-semibold text-slate-700">暂无补救建议</h3>
        <p className="mt-1 text-sm text-slate-500">
          代理会在检测到血糖风险时自动推送补救行动。
        </p>
      </div>
    )
  }

  if (visible.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center">
        <div className="text-4xl">✅</div>
        <h3 className="mt-3 font-heading text-lg font-semibold text-emerald-700">当前无需补救</h3>
        <p className="mt-1 text-sm text-slate-500">
          你的血糖状态看起来不错，继续保持！
        </p>
      </div>
    )
  }

  return (
    <div className="grid gap-4">
      {visible.map((action) => (
        <RescueActionCard
          key={action.id}
          action={action}
          onFeedback={handleFeedback}
          feedbackPending={feedback.isPending}
        />
      ))}
    </div>
  )
}
