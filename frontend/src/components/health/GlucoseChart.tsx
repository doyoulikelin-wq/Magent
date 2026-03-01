import { useMemo, useState } from 'react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import type { GlucosePoint } from '../../api/types'

type WindowOption = '24h' | '3d' | '7d' | 'all'

type Props = {
  points: GlucosePoint[]
  rangeMin: string | null
  rangeMax: string | null
}

export function GlucoseChart({ points, rangeMin, rangeMax }: Props) {
  const [window, setWindow] = useState<WindowOption>('all')

  const filtered = useMemo(() => {
    if (!points.length) return []
    if (window === 'all') return points

    const maxTs = rangeMax ? new Date(rangeMax).getTime() : Date.now()
    const hours = window === '24h' ? 24 : window === '3d' ? 72 : 168
    const cutoff = maxTs - hours * 3600_000
    return points.filter((p) => new Date(p.ts).getTime() >= cutoff)
  }, [points, window, rangeMax])

  const chartData = useMemo(() => {
    return filtered.map((p) => ({
      ts: new Date(p.ts).getTime(),
      glucose: p.glucose_mgdl,
    }))
  }, [filtered])

  const windows: { key: WindowOption; label: string }[] = [
    { key: '24h', label: '24h' },
    { key: '3d', label: '3天' },
    { key: '7d', label: '7天' },
    { key: 'all', label: '全部' },
  ]

  // Stats
  const stats = useMemo(() => {
    if (!chartData.length) return null
    const vals = chartData.map((d) => d.glucose)
    const avg = vals.reduce((a, b) => a + b, 0) / vals.length
    const inRange = vals.filter((v) => v >= 70 && v <= 180).length
    return {
      avg: Math.round(avg),
      min: Math.min(...vals),
      max: Math.max(...vals),
      tir: Math.round((inRange / vals.length) * 100),
      count: vals.length,
    }
  }, [chartData])

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <h3 className="font-heading text-lg font-semibold text-slate-900">血糖趋势</h3>
          {stats && (
            <div className="mt-0.5 flex gap-3 text-xs text-slate-500">
              <span>均值 <b className="text-primary">{stats.avg}</b> mg/dL</span>
              <span>范围 {stats.min}–{stats.max}</span>
              <span>TIR <b className="text-emerald-600">{stats.tir}%</b></span>
              <span>{stats.count} 点</span>
            </div>
          )}
        </div>
        <div className="flex gap-1">
          {windows.map((w) => (
            <button
              key={w.key}
              onClick={() => setWindow(w.key)}
              className={`rounded-lg px-2 py-1 text-xs font-medium transition ${
                window === w.key
                  ? 'bg-primary text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {w.label}
            </button>
          ))}
        </div>
      </div>

      {chartData.length === 0 ? (
        <div className="flex h-64 items-center justify-center rounded-xl bg-slate-50 text-sm text-slate-500">
          {points.length === 0 ? '暂无血糖数据，请先导入' : `该时间窗口内无数据`}
        </div>
      ) : (
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="glucoseArea" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#0f766e" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="#0f766e" stopOpacity={0.04} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis
                dataKey="ts"
                type="number"
                domain={['dataMin', 'dataMax']}
                scale="time"
                tickFormatter={(ts: number) => {
                  const d = new Date(ts)
                  if (window === '24h') return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
                  return d.toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' })
                }}
                minTickGap={40}
                tick={{ fontSize: 11 }}
              />
              <YAxis domain={[40, 250]} tick={{ fontSize: 11 }} tickCount={6} />
              <Tooltip
                labelFormatter={(ts: number) =>
                  new Date(ts).toLocaleString('zh-CN', {
                    month: 'numeric',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })
                }
                formatter={(value: number) => [`${value} mg/dL`, '血糖']}
              />
              {/* TIR range band */}
              <ReferenceLine y={70} stroke="#f59e0b" strokeDasharray="4 4" strokeWidth={1} />
              <ReferenceLine y={180} stroke="#f59e0b" strokeDasharray="4 4" strokeWidth={1} />
              <Area
                type="monotone"
                dataKey="glucose"
                stroke="#0f766e"
                fill="url(#glucoseArea)"
                strokeWidth={1.5}
                dot={false}
                animationDuration={600}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {rangeMin && rangeMax && (
        <div className="mt-2 text-center text-[10px] text-slate-400">
          数据范围: {new Date(rangeMin).toLocaleDateString('zh-CN')} – {new Date(rangeMax).toLocaleDateString('zh-CN')}
        </div>
      )}
    </div>
  )
}
