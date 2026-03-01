import type { DailyPlanAction, RescueAction, TodayBriefing } from '../../api/types'

function RiskBadge({ risk }: { risk: string }) {
  const colors: Record<string, string> = {
    low: 'bg-emerald-100 text-emerald-700',
    medium: 'bg-amber-100 text-amber-700',
    high: 'bg-red-100 text-red-700',
  }
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${colors[risk] ?? 'bg-slate-100 text-slate-600'}`}>
      {risk === 'low' ? '低' : risk === 'medium' ? '中' : risk === 'high' ? '高' : risk}
    </span>
  )
}

function GlucoseStatus({ status }: { status: TodayBriefing['glucose_status'] }) {
  const trendIcon = status.trend === 'rising' ? '↑' : status.trend === 'falling' ? '↓' : '→'
  return (
    <div className="flex items-center gap-3 rounded-xl bg-primary/5 p-3">
      <div className="text-3xl font-bold text-primary">
        {status.current_mgdl ?? '--'}
        <span className="ml-1 text-sm font-normal text-slate-500">mg/dL {trendIcon}</span>
      </div>
      {status.tir_24h != null && (
        <div className="text-sm text-slate-600">
          TIR 24h: <span className="font-semibold">{(status.tir_24h * 100).toFixed(0)}%</span>
        </div>
      )}
    </div>
  )
}

function DailyPlanSection({ plan }: { plan: DailyPlanAction }) {
  const p = plan.payload
  return (
    <div className="space-y-3">
      <h4 className="font-heading text-sm font-semibold text-slate-700">{p.title}</h4>
      {p.risk_windows.length > 0 && (
        <div>
          <div className="mb-1 text-xs text-slate-500">高风险时段</div>
          <div className="flex flex-wrap gap-2">
            {p.risk_windows.map((w, i) => (
              <div key={i} className="flex items-center gap-1 rounded-lg border border-slate-200 px-2 py-1 text-sm">
                <span>{w.start} – {w.end}</span>
                <RiskBadge risk={w.risk} />
              </div>
            ))}
          </div>
        </div>
      )}
      {p.today_goals.length > 0 && (
        <div>
          <div className="mb-1 text-xs text-slate-500">今日目标</div>
          <ul className="list-inside list-disc space-y-1 text-sm text-slate-700">
            {p.today_goals.map((g, i) => <li key={i}>{g}</li>)}
          </ul>
        </div>
      )}
      {plan.trace_id && (
        <div className="text-[10px] text-slate-400">trace: {plan.trace_id}</div>
      )}
    </div>
  )
}

function PendingRescues({ rescues }: { rescues: RescueAction[] }) {
  if (rescues.length === 0) return null
  return (
    <div className="space-y-2">
      <h4 className="font-heading text-sm font-semibold text-red-600">待处理补救</h4>
      {rescues.map((r) => (
        <div key={r.id} className="rounded-lg border border-red-200 bg-red-50 p-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-red-800">{r.payload.title}</span>
            <RiskBadge risk={r.payload.risk_level} />
          </div>
          <div className="mt-1 text-xs text-red-600">
            {r.payload.steps.map((s) => s.label).join(' · ')}
          </div>
        </div>
      ))}
    </div>
  )
}

type Props = {
  data: TodayBriefing
}

export function TodayBriefingCard({ data }: Props) {
  return (
    <div className="grid gap-4">
      {/* 血糖状态 */}
      <GlucoseStatus status={data.glucose_status} />

      {/* 日计划 */}
      {data.daily_plan && (
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
          <DailyPlanSection plan={data.daily_plan} />
        </div>
      )}

      {/* 待处理补救 */}
      {data.pending_rescues.length > 0 && (
        <div className="rounded-2xl border border-red-200 bg-white p-4 shadow-soft">
          <PendingRescues rescues={data.pending_rescues} />
        </div>
      )}

      {/* 近期动作摘要 */}
      {data.recent_actions.length > 0 && (
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
          <h4 className="font-heading text-sm font-semibold text-slate-700">近期动作</h4>
          <div className="mt-2 space-y-2">
            {data.recent_actions.slice(0, 5).map((a) => (
              <div key={a.id} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm">
                <span className="text-slate-700">{a.payload.title}</span>
                <span className="text-xs text-slate-400">
                  {new Date(a.created_ts).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
