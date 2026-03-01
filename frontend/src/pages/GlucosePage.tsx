import { useMemo, useState } from 'react'
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { useGlucosePoints, useGlucoseRange } from '../api/hooks'
import type { GlucosePoint } from '../api/types'

const BINGE_THRESHOLD_KCAL = 800

type ViewMode = '24h' | 'all'

/* ── helpers ────────────────────────────────────────────── */

/** Group points by calendar day (local timezone) */
function groupByDay(pts: GlucosePoint[]): Map<string, GlucosePoint[]> {
  const map = new Map<string, GlucosePoint[]>()
  for (const p of pts) {
    const key = new Date(p.ts).toLocaleDateString('zh-CN')
    const arr = map.get(key) ?? []
    arr.push(p)
    map.set(key, arr)
  }
  return map
}

/** Convert absolute timestamp to minutes-since-midnight for overlay charts */
function toMinuteOfDay(ts: string): number {
  const d = new Date(ts)
  return d.getHours() * 60 + d.getMinutes()
}

function fmtTime(min: number): string {
  const h = Math.floor(min / 60)
  const m = min % 60
  return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`
}

/* ── Binge markers (meal data from query or props) ────── */
// For now, we'll show binge markers from the meal events stored with the glucose data
// The meal data API returns meals with kcal, we'll pass them in

type BingeMeal = {
  ts: string
  kcal: number
}

/* ── Component ──────────────────────────────────────────── */

export function GlucosePage() {
  const { data: range } = useGlucoseRange()

  const [mode, setMode] = useState<ViewMode>('all')
  const [showBinge, setShowBinge] = useState(true)

  // Fetch all points (downsample to 2000)
  const from = range?.min_ts ?? null
  const to = range?.max_ts ?? null
  const { data: allPoints = [], isLoading } = useGlucosePoints(from, to)

  // TODO: fetch real meals — for now we simulate binge markers from points
  // In the real version, meals will be fetched from /api/meals
  const bingeMeals: BingeMeal[] = useMemo(() => {
    // placeholder: no meal data yet — we'll wire this up when meal API is used
    return []
  }, [])

  /* ── ALL mode data ────────────────────────────────────── */
  const allChartData = useMemo(() => {
    return allPoints.map((p) => ({
      ts: new Date(p.ts).getTime(),
      glucose: p.glucose_mgdl,
    }))
  }, [allPoints])

  /* ── 24h mode data (today red, past gray, avg blue) ──── */
  const { todayData, pastDays, avgBaseline, todayKey } = useMemo(() => {
    if (!allPoints.length) return { todayData: [], pastDays: [] as { minute: number; glucose: number }[][], avgBaseline: [] as { minute: number; glucose: number }[], todayKey: '' }

    const byDay = groupByDay(allPoints)
    const dayKeys = [...byDay.keys()].sort()
    const latestDay = dayKeys[dayKeys.length - 1]

    // Today's data
    const todayPts = (byDay.get(latestDay) ?? []).map((p) => ({
      minute: toMinuteOfDay(p.ts),
      glucose: p.glucose_mgdl,
    }))

    // Past days
    const pastDaysArr = dayKeys
      .filter((k) => k !== latestDay)
      .map((k) =>
        (byDay.get(k) ?? []).map((p) => ({
          minute: toMinuteOfDay(p.ts),
          glucose: p.glucose_mgdl,
        })),
      )

    // Average baseline (per 15-min bucket across all days)
    const buckets = new Map<number, number[]>()
    for (const p of allPoints) {
      const m = toMinuteOfDay(p.ts)
      const bucket = Math.floor(m / 15) * 15
      const arr = buckets.get(bucket) ?? []
      arr.push(p.glucose_mgdl)
      buckets.set(bucket, arr)
    }
    const avgLine = [...buckets.entries()]
      .sort(([a], [b]) => a - b)
      .map(([minute, vals]) => ({
        minute,
        glucose: Math.round(vals.reduce((s, v) => s + v, 0) / vals.length),
      }))

    return { todayData: todayPts, pastDays: pastDaysArr, avgBaseline: avgLine, todayKey: latestDay }
  }, [allPoints])

  /* ── Stats ────────────────────────────────────────────── */
  const stats = useMemo(() => {
    const pts = mode === '24h' ? todayData : allChartData
    if (!pts.length) return null
    const vals = pts.map((d) => d.glucose)
    const avg = vals.reduce((a, b) => a + b, 0) / vals.length
    const inRange = vals.filter((v) => v >= 70 && v <= 180).length
    return {
      avg: Math.round(avg),
      min: Math.min(...vals),
      max: Math.max(...vals),
      tir: Math.round((inRange / vals.length) * 100),
      count: vals.length,
    }
  }, [mode, todayData, allChartData])

  /* ── Find binge-adjacent glucosePoints ─────────────────── */
  const bingeTimestamps = useMemo(() => {
    if (!showBinge) return new Set<number>()
    return new Set(
      bingeMeals
        .filter((m) => m.kcal >= BINGE_THRESHOLD_KCAL)
        .map((m) => new Date(m.ts).getTime()),
    )
  }, [bingeMeals, showBinge])

  // Mark all-mode data with binge flag
  const allChartDataWithBinge = useMemo(() => {
    if (!bingeTimestamps.size) return allChartData
    return allChartData.map((d) => {
      // Mark points within 30 min of a binge meal
      for (const bt of bingeTimestamps) {
        if (Math.abs(d.ts - bt) < 30 * 60_000) {
          return { ...d, binge: d.glucose }
        }
      }
      return d
    })
  }, [allChartData, bingeTimestamps])

  return (
    <div className="mx-auto max-w-2xl px-4 pb-24 pt-6">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="font-heading text-xl font-bold text-slate-800">动态数据</h2>
          {stats && (
            <div className="mt-0.5 flex flex-wrap gap-2 text-xs text-slate-500">
              <span>
                均值 <b className="text-teal-600">{stats.avg}</b> mg/dL
              </span>
              <span>{stats.min}–{stats.max}</span>
              <span>
                TIR <b className="text-emerald-600">{stats.tir}%</b>
              </span>
              <span>{stats.count} 点</span>
            </div>
          )}
        </div>
      </div>

      {/* Controls */}
      <div className="mb-4 flex items-center gap-3">
        <div className="flex rounded-xl bg-slate-100 p-0.5">
          {(['all', '24h'] as ViewMode[]).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`rounded-lg px-4 py-1.5 text-sm font-medium transition ${
                mode === m ? 'bg-white text-teal-700 shadow-sm' : 'text-slate-500'
              }`}
            >
              {m === 'all' ? '全部' : '24h'}
            </button>
          ))}
        </div>

        <label className="ml-auto flex items-center gap-1.5 text-xs">
          <input
            type="checkbox"
            checked={showBinge}
            onChange={(e) => setShowBinge(e.target.checked)}
            className="h-3.5 w-3.5 rounded border-slate-300 text-rose-500 accent-rose-500"
          />
          <span className="text-slate-600">暴食标记</span>
        </label>
      </div>

      {/* Chart */}
      {isLoading ? (
        <div className="flex h-72 items-center justify-center rounded-xl bg-white text-sm text-slate-400">
          加载数据中...
        </div>
      ) : allPoints.length === 0 ? (
        <div className="flex h-72 items-center justify-center rounded-xl bg-white text-sm text-slate-500">
          暂无血糖数据
        </div>
      ) : mode === 'all' ? (
        /* ── ALL MODE ─────────────────────────────────────── */
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={allChartDataWithBinge}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis
                  dataKey="ts"
                  type="number"
                  domain={['dataMin', 'dataMax']}
                  scale="time"
                  tickFormatter={(ts: number) =>
                    new Date(ts).toLocaleDateString('zh-CN', {
                      month: 'numeric',
                      day: 'numeric',
                    })
                  }
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
                  formatter={(value: number, name: string) => [
                    `${value} mg/dL`,
                    name === 'binge' ? '🔴 暴食区间' : '血糖',
                  ]}
                />
                <ReferenceLine y={70} stroke="#f59e0b" strokeDasharray="4 4" strokeWidth={1} />
                <ReferenceLine y={180} stroke="#f59e0b" strokeDasharray="4 4" strokeWidth={1} />
                <Line
                  type="monotone"
                  dataKey="glucose"
                  stroke="#0f766e"
                  strokeWidth={1.5}
                  dot={false}
                  animationDuration={600}
                />
                {showBinge && (
                  <Line
                    type="monotone"
                    dataKey="binge"
                    stroke="#ef4444"
                    strokeWidth={3}
                    dot={{ r: 4, fill: '#ef4444' }}
                    animationDuration={300}
                    connectNulls={false}
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>

          {range?.min_ts && range?.max_ts && (
            <div className="mt-2 text-center text-[10px] text-slate-400">
              {new Date(range.min_ts).toLocaleDateString('zh-CN')} –{' '}
              {new Date(range.max_ts).toLocaleDateString('zh-CN')}
            </div>
          )}
        </div>
      ) : (
        /* ── 24H MODE ─────────────────────────────────────── */
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="mb-2 flex items-center gap-4 text-xs">
            <span className="flex items-center gap-1">
              <span className="inline-block h-2 w-4 rounded bg-red-500" />
              今天 ({todayKey})
            </span>
            <span className="flex items-center gap-1">
              <span className="inline-block h-2 w-4 rounded bg-slate-300" />
              过往
            </span>
            <span className="flex items-center gap-1">
              <span className="inline-block h-2 w-4 rounded bg-blue-500" />
              平均基线
            </span>
          </div>

          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis
                  dataKey="minute"
                  type="number"
                  domain={[0, 1440]}
                  tickFormatter={fmtTime}
                  ticks={[0, 180, 360, 540, 720, 900, 1080, 1260, 1440]}
                  tick={{ fontSize: 10 }}
                />
                <YAxis domain={[40, 250]} tick={{ fontSize: 11 }} tickCount={6} />
                <Tooltip
                  labelFormatter={(min: number) => fmtTime(min as number)}
                  formatter={(value: number) => [`${value} mg/dL`]}
                />
                <ReferenceLine y={70} stroke="#f59e0b" strokeDasharray="4 4" strokeWidth={1} />
                <ReferenceLine y={180} stroke="#f59e0b" strokeDasharray="4 4" strokeWidth={1} />

                {/* Past days - gray */}
                {pastDays.map((dayPts, i) => (
                  <Line
                    key={`past-${i}`}
                    data={dayPts}
                    type="monotone"
                    dataKey="glucose"
                    stroke="#cbd5e1"
                    strokeWidth={1}
                    dot={false}
                    animationDuration={0}
                    name={`过往${i + 1}`}
                  />
                ))}

                {/* Average baseline - blue */}
                <Line
                  data={avgBaseline}
                  type="monotone"
                  dataKey="glucose"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  strokeDasharray="6 3"
                  dot={false}
                  animationDuration={400}
                  name="平均基线"
                />

                {/* Today - red */}
                <Line
                  data={todayData}
                  type="monotone"
                  dataKey="glucose"
                  stroke="#ef4444"
                  strokeWidth={2.5}
                  dot={false}
                  animationDuration={600}
                  name="今天"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
        <b>暴食标记：</b>单餐卡路里 ≥ {BINGE_THRESHOLD_KCAL} kcal 的进食事件将在血糖曲线上以红色标注。
        当前数据中检测到 <b>{bingeMeals.filter((m) => m.kcal >= BINGE_THRESHOLD_KCAL).length}</b> 次暴食事件。
        {!showBinge && <span className="ml-1 text-slate-500">（已隐藏标记）</span>}
      </div>
    </div>
  )
}
