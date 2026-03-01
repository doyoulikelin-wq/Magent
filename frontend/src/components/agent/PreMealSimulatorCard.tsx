import { useState } from 'react'

import type { PreMealSimPayload } from '../../api/types'

type Props = {
  onSimulate: (input: { kcal: number; meal_time: string }) => void
  isPending: boolean
  result: PreMealSimPayload | null
}

export function PreMealSimulatorCard({ onSimulate, isPending, result }: Props) {
  const [kcal, setKcal] = useState(500)
  const [time, setTime] = useState(() => {
    const now = new Date()
    return `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`
  })

  function handleSubmit() {
    const today = new Date().toISOString().slice(0, 10)
    onSimulate({ kcal, meal_time: `${today}T${time}:00` })
  }

  return (
    <div className="grid gap-4">
      {/* 输入区 */}
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
        <h3 className="font-heading text-lg font-semibold text-slate-900">输入即将吃的食物</h3>
        <p className="mt-1 text-sm text-slate-500">系统将预测餐后血糖响应并给出替代方案</p>

        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <label className="grid gap-1">
            <span className="text-sm text-slate-600">预估热量 (kcal)</span>
            <input
              type="number"
              min={50}
              max={3000}
              step={50}
              value={kcal}
              onChange={(e) => setKcal(Number(e.target.value))}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
          </label>
          <label className="grid gap-1">
            <span className="text-sm text-slate-600">用餐时间</span>
            <input
              type="time"
              value={time}
              onChange={(e) => setTime(e.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
          </label>
        </div>

        <button
          onClick={handleSubmit}
          disabled={isPending}
          className="mt-4 w-full rounded-xl bg-primary px-4 py-3 text-sm font-semibold text-white shadow-soft transition hover:bg-primary/90 disabled:bg-slate-300 sm:w-auto"
        >
          {isPending ? '预演中...' : '立即预演'}
        </button>
      </div>

      {/* 预测结果 */}
      {result && (
        <div className="rounded-2xl border border-primary/20 bg-primary/5 p-4 shadow-soft">
          <h3 className="font-heading text-lg font-semibold text-primary">{result.title}</h3>

          <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Metric label="预测峰值" value={`${result.prediction.peak_glucose.toFixed(1)} mmol/L`} />
            <Metric label="达峰时间" value={`${result.prediction.time_to_peak_min} 分钟`} />
            <Metric label="AUC 2h" value={result.prediction.auc_0_120.toFixed(1)} />
            {result.prediction.liver_load_score != null && (
              <Metric label="肝脏负担" value={`${(result.prediction.liver_load_score * 100).toFixed(0)}%`} />
            )}
          </div>

          {result.alternatives.length > 0 && (
            <div className="mt-4">
              <div className="mb-2 text-sm font-medium text-slate-700">替代方案</div>
              <div className="grid gap-2 sm:grid-cols-2">
                {result.alternatives.map((alt) => (
                  <div
                    key={alt.id}
                    className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-3 py-2"
                  >
                    <span className="text-sm text-slate-700">{alt.label}</span>
                    <span className={`text-sm font-semibold ${alt.expected_delta_peak < 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                      {alt.expected_delta_peak > 0 ? '+' : ''}{alt.expected_delta_peak.toFixed(1)} mmol/L
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-white/80 p-2 text-center">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="text-lg font-bold text-slate-900">{value}</div>
    </div>
  )
}
