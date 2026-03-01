import type { RescueAction } from '../../api/types'

type Props = {
  action: RescueAction
  onFeedback?: (actionId: string, choice: 'executed' | 'not_executed' | 'partial') => void
  feedbackPending?: boolean
}

export function RescueActionCard({ action, onFeedback, feedbackPending }: Props) {
  const p = action.payload
  const isDegraded = action.status === 'degraded'

  return (
    <div className={`rounded-2xl border p-4 shadow-soft ${isDegraded ? 'border-amber-200 bg-amber-50/50' : 'border-red-200 bg-white'}`}>
      {isDegraded && (
        <div className="mb-3 rounded-lg bg-amber-100 px-3 py-1.5 text-xs font-medium text-amber-700">
          ⚠️ 已安全降级 — 部分信息不可用，建议仅供参考
        </div>
      )}

      {/* 标题行 */}
      <div className="flex items-start justify-between">
        <h3 className="font-heading text-lg font-semibold text-slate-900">{p.title}</h3>
        <RiskBadge level={p.risk_level} />
      </div>

      {/* 为什么触发 */}
      <div className="mt-3">
        <div className="text-xs font-medium uppercase tracking-wider text-slate-400">为什么触发</div>
        <div className="mt-1 flex flex-wrap gap-1">
          {p.trigger_evidence.map((e, i) => (
            <span key={i} className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">{e}</span>
          ))}
        </div>
        {action.reason_evidence.summary && (
          <p className="mt-1 text-sm text-slate-600">{action.reason_evidence.summary}</p>
        )}
      </div>

      {/* 建议动作 */}
      <div className="mt-3">
        <div className="text-xs font-medium uppercase tracking-wider text-slate-400">建议动作</div>
        <div className="mt-1 space-y-1.5">
          {p.steps.map((step) => (
            <div key={step.id} className="flex items-center gap-2 rounded-lg bg-primary/5 px-3 py-2">
              <span className="text-base">✅</span>
              <span className="text-sm font-medium text-slate-700">{step.label}</span>
              {step.duration_min && (
                <span className="ml-auto text-xs text-slate-500">{step.duration_min} 分钟</span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* 预计收益 */}
      <div className="mt-3">
        <div className="text-xs font-medium uppercase tracking-wider text-slate-400">预计收益</div>
        <div className="mt-1 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
          峰值预计下降 {p.expected_effect.delta_peak_low.toFixed(1)} – {p.expected_effect.delta_peak_high.toFixed(1)} mmol/L
        </div>
      </div>

      {/* 复盘打点 */}
      {p.followup?.checkpoints_min && (
        <div className="mt-3 text-xs text-slate-500">
          复盘时间点: {p.followup.checkpoints_min.map((m) => `${m}min`).join(' → ')}
        </div>
      )}

      {/* 反馈按钮 */}
      {onFeedback && (
        <div className="mt-4 flex flex-wrap gap-2">
          {(['executed', 'partial', 'not_executed'] as const).map((choice) => (
            <button
              key={choice}
              disabled={feedbackPending}
              onClick={() => onFeedback(action.id, choice)}
              className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs transition hover:bg-slate-100 disabled:opacity-50"
            >
              {choice === 'executed' ? '已执行' : choice === 'partial' ? '部分执行' : '未执行'}
            </button>
          ))}
        </div>
      )}

      {/* trace */}
      {action.trace_id && (
        <div className="mt-2 text-[10px] text-slate-400">trace: {action.trace_id}</div>
      )}
    </div>
  )
}

function RiskBadge({ level }: { level: string }) {
  const colors: Record<string, string> = {
    low: 'bg-emerald-100 text-emerald-700',
    medium: 'bg-amber-100 text-amber-700',
    high: 'bg-red-100 text-red-700',
  }
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${colors[level] ?? 'bg-slate-100 text-slate-600'}`}>
      {level === 'low' ? '低风险' : level === 'medium' ? '中风险' : level === 'high' ? '高风险' : level}
    </span>
  )
}
