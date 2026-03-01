import type { HealthDashboard } from '../../api/types'

type Props = {
  data: HealthDashboard
}

function card(label: string, value: string, tone?: 'accent') {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className={['mt-2 text-3xl font-semibold', tone ? 'text-accent' : 'text-slate-900'].join(' ')}>{value}</div>
    </div>
  )
}

export function MetricsCards({ data }: Props) {
  const avg = data.glucose.last_24h.avg == null ? '--' : `${Math.round(data.glucose.last_24h.avg)} mg/dL`
  const tir =
    data.glucose.last_7d.tir_70_180_pct == null
      ? '--'
      : `${Math.round(data.glucose.last_7d.tir_70_180_pct)}%`

  return (
    <div className="grid gap-4 md:grid-cols-3">
      {card('24h 平均血糖', avg)}
      {card('7d TIR 70-180', tir)}
      {card('今日摄入', `${data.kcal_today} kcal`, 'accent')}
    </div>
  )
}
