import { useState } from 'react'

import { useGlucoseRange, useHealthReports } from '../api/hooks'
import type { ExamPhase, LabItem } from '../api/types'

/**
 * 健康数据页 – 时间轴 + 体检报告 + 上传入口
 *
 * CGM 用户：显示血糖数据范围
 * Liver 用户：显示已解析的体检报告（初始 / 结束）
 */
export function HealthDataPage() {
  const { data: range, isLoading: glucoseLoading } = useGlucoseRange()
  const { data: report, isLoading: reportLoading } = useHealthReports()
  const subjectId = localStorage.getItem('metabodash_subject')
  const [uploadMsg, setUploadMsg] = useState('')

  const isLoading = glucoseLoading || reportLoading

  // ── Timeline events ───────────────────────────────────────

  const events: { date: string; label: string; icon: string; color: string }[] = []

  if (range?.min_ts) {
    events.push({
      date: new Date(range.min_ts).toLocaleDateString('zh-CN'),
      label: `开始监测血糖（${range.count} 条记录）`,
      icon: '📈',
      color: 'bg-teal-100 border-teal-300',
    })
  }
  if (range?.max_ts) {
    events.push({
      date: new Date(range.max_ts).toLocaleDateString('zh-CN'),
      label: '最近一次血糖数据',
      icon: '✅',
      color: 'bg-emerald-100 border-emerald-300',
    })
  }

  // Add exam report events for Liver subjects
  if (report?.phases) {
    for (const ph of report.phases) {
      events.push({
        date: ph.dates?.[0] ?? '—',
        label: `${ph.label}（${ph.items.length} 项检查）`,
        icon: ph.phase === '初始' ? '🔬' : '📋',
        color: ph.phase === '初始' ? 'bg-orange-100 border-orange-300' : 'bg-blue-100 border-blue-300',
      })
    }
  }

  // If no events at all, show placeholder
  if (events.length === 0 && !isLoading) {
    events.push({
      date: '待上传',
      label: '体检报告 / 肝功能检查',
      icon: '📋',
      color: 'bg-slate-100 border-slate-300',
    })
  }

  return (
    <div className="mx-auto max-w-lg px-4 pb-24 pt-6">
      {/* Header */}
      <div className="mb-6">
        <h2 className="font-heading text-xl font-bold text-slate-800">健康数据</h2>
        {subjectId && (
          <p className="mt-0.5 text-sm text-slate-500">
            受试者 <span className="font-semibold text-teal-600">{subjectId}</span> 的健康时间轴
          </p>
        )}
        {report?.patient?.name && (
          <p className="mt-0.5 text-xs text-slate-400">
            {report.patient.name}　{report.patient.sex ?? ''}　{report.patient.age ?? ''}
          </p>
        )}
      </div>

      {/* Timeline */}
      {isLoading ? (
        <div className="rounded-xl bg-white p-8 text-center text-sm text-slate-400">加载中...</div>
      ) : (
        <div className="relative ml-4 border-l-2 border-slate-200 pl-6">
          {events.map((ev, i) => (
            <div key={i} className="relative mb-6 last:mb-0">
              {/* Dot */}
              <div className="absolute -left-[33px] top-1 flex h-5 w-5 items-center justify-center rounded-full border-2 border-white bg-white shadow">
                <span className="text-xs">{ev.icon}</span>
              </div>
              {/* Card */}
              <div className={`rounded-xl border p-4 ${ev.color}`}>
                <div className="text-xs font-medium text-slate-500">{ev.date}</div>
                <div className="mt-1 text-sm font-medium text-slate-700">{ev.label}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Exam Report Panels for Liver subjects */}
      {report?.phases && report.phases.length > 0 && (
        <div className="mt-8 space-y-6">
          {report.phases.map((ph) => (
            <ExamPhasePanel key={ph.phase} phase={ph} />
          ))}

          {/* Comparison of key markers if both phases available */}
          {report.phases.length === 2 && (
            <KeyMarkerComparison phases={report.phases} />
          )}
        </div>
      )}

      {/* Data summary cards */}
      {range && range.count > 0 && (
        <div className="mt-6 grid grid-cols-2 gap-3">
          <div className="rounded-xl border border-slate-200 bg-white p-4 text-center">
            <div className="text-2xl font-bold text-teal-600">{range.count.toLocaleString()}</div>
            <div className="mt-1 text-xs text-slate-500">血糖数据点</div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 text-center">
            <div className="text-2xl font-bold text-cyan-600">
              {range.min_ts && range.max_ts
                ? Math.ceil(
                    (new Date(range.max_ts).getTime() - new Date(range.min_ts).getTime()) /
                      86400_000,
                  )
                : 0}
            </div>
            <div className="mt-1 text-xs text-slate-500">监测天数</div>
          </div>
        </div>
      )}

      {/* Upload section – only show for subjects without exam data */}
      {(!report?.phases || report.phases.length === 0) && (
        <div className="mt-8 rounded-2xl border-2 border-dashed border-slate-300 bg-white p-6 text-center">
          <div className="text-3xl">📤</div>
          <h3 className="mt-2 font-semibold text-slate-700">上传健康报告</h3>
          <p className="mt-1 text-xs text-slate-500">支持 PDF、图片等格式（功能开发中）</p>
          <button
            onClick={() => setUploadMsg('功能即将上线，敬请期待！')}
            className="mt-4 rounded-xl bg-teal-600 px-6 py-2 text-sm font-medium text-white shadow transition hover:bg-teal-700"
          >
            选择文件上传
          </button>
          {uploadMsg && <p className="mt-3 text-xs text-amber-600">{uploadMsg}</p>}
        </div>
      )}
    </div>
  )
}

// ── Exam Phase Panel ────────────────────────────────────────

/** Collapsible panel showing lab items for one exam phase. */
function ExamPhasePanel({ phase }: { phase: ExamPhase }) {
  const [expanded, setExpanded] = useState(phase.phase === '初始')
  const abnormalCount = phase.items.filter((i) => i.abnormal).length

  // Group items by order_name
  const groups = groupByOrder(phase.items)

  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between px-5 py-4 text-left"
      >
        <div>
          <div className="flex items-center gap-2">
            <span className={`inline-block h-3 w-3 rounded-full ${phase.phase === '初始' ? 'bg-orange-400' : 'bg-blue-400'}`} />
            <span className="font-semibold text-slate-800">{phase.label}</span>
          </div>
          <div className="mt-1 flex items-center gap-3 text-xs text-slate-500">
            <span>{phase.dates?.join(' / ')}</span>
            <span>{phase.items.length} 项</span>
            {abnormalCount > 0 && (
              <span className="rounded-full bg-red-100 px-2 py-0.5 text-red-600 font-medium">
                {abnormalCount} 项异常
              </span>
            )}
          </div>
        </div>
        <span className={`text-slate-400 transition-transform ${expanded ? 'rotate-180' : ''}`}>
          ▼
        </span>
      </button>

      {/* Body */}
      {expanded && (
        <div className="border-t border-slate-100 px-5 pb-4 pt-3">
          {groups.map(([orderName, items]) => (
            <div key={orderName} className="mb-4 last:mb-0">
              {orderName && (
                <div className="mb-2 text-xs font-medium text-slate-400 truncate" title={orderName}>
                  📎 {orderName}
                </div>
              )}
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-left text-slate-400">
                      <th className="pb-1 pr-3 font-medium">项目</th>
                      <th className="pb-1 pr-3 font-medium text-right">结果</th>
                      <th className="pb-1 pr-3 font-medium">单位</th>
                      <th className="pb-1 font-medium">参考范围</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((item, j) => (
                      <LabItemRow key={j} item={item} />
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Lab Item Row ────────────────────────────────────────────

function LabItemRow({ item }: { item: LabItem }) {
  const isAbnormal = !!item.abnormal
  return (
    <tr className={isAbnormal ? 'bg-red-50' : ''}>
      <td className="py-1 pr-3 text-slate-700">
        {item.name}
        {isAbnormal && (
          <span className="ml-1 text-red-500 font-bold">{item.abnormal}</span>
        )}
      </td>
      <td className={`py-1 pr-3 text-right font-mono font-medium ${isAbnormal ? 'text-red-600' : 'text-slate-800'}`}>
        {item.value ?? '—'}
      </td>
      <td className="py-1 pr-3 text-slate-500">{item.unit ?? ''}</td>
      <td className="py-1 text-slate-400">{item.reference ?? ''}</td>
    </tr>
  )
}

// ── Key Marker Comparison ───────────────────────────────────

/** Compare key liver markers between 初始 and 结束 phases */
function KeyMarkerComparison({ phases }: { phases: ExamPhase[] }) {
  const keyMarkers = [
    '谷丙转氨酶',
    '谷草转氨酶',
    '总胆红素',
    '甘油三酯',
    '总胆固醇',
    '空腹血糖',
    '糖化血红蛋白',
    '尿酸',
    '白蛋白',
    '高密度脂蛋白胆固醇',
    '低密度脂蛋白胆固醇',
  ]

  const initItems = phases.find((p) => p.phase === '初始')?.items ?? []
  const endItems = phases.find((p) => p.phase === '结束')?.items ?? []

  const comparisons: {
    name: string
    init: string | null
    end: string | null
    unit: string | null
    delta: number | null
  }[] = []

  for (const marker of keyMarkers) {
    const init = initItems.find((i) => i.name === marker)
    const end = endItems.find((i) => i.name === marker)
    if (init || end) {
      const initVal = init?.value ? parseFloat(init.value) : null
      const endVal = end?.value ? parseFloat(end.value) : null
      comparisons.push({
        name: marker,
        init: init?.value ?? null,
        end: end?.value ?? null,
        unit: init?.unit ?? end?.unit ?? null,
        delta: initVal != null && endVal != null ? endVal - initVal : null,
      })
    }
  }

  if (comparisons.length === 0) return null

  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
      <div className="px-5 py-4">
        <h3 className="flex items-center gap-2 font-semibold text-slate-800">
          <span>📊</span> 关键指标对比
        </h3>
        <p className="mt-1 text-xs text-slate-400">
          {phases[0].dates?.[0]} → {phases[1].dates?.[0]}
        </p>
      </div>
      <div className="border-t border-slate-100 px-5 pb-4 pt-3">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left text-slate-400">
              <th className="pb-2 pr-2 font-medium">指标</th>
              <th className="pb-2 pr-2 font-medium text-right">初始</th>
              <th className="pb-2 pr-2 font-medium text-right">结束</th>
              <th className="pb-2 font-medium text-right">变化</th>
            </tr>
          </thead>
          <tbody>
            {comparisons.map((c) => (
              <tr key={c.name} className="border-t border-slate-50">
                <td className="py-1.5 pr-2 text-slate-700">{c.name}</td>
                <td className="py-1.5 pr-2 text-right font-mono text-slate-600">
                  {c.init ?? '—'}
                </td>
                <td className="py-1.5 pr-2 text-right font-mono text-slate-600">
                  {c.end ?? '—'}
                </td>
                <td className="py-1.5 text-right font-mono font-medium">
                  {c.delta != null ? (
                    <span className={c.delta < 0 ? 'text-green-600' : c.delta > 0 ? 'text-red-500' : 'text-slate-400'}>
                      {c.delta > 0 ? '+' : ''}{c.delta.toFixed(2)}
                    </span>
                  ) : (
                    <span className="text-slate-300">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Utilities ────────────────────────────────────────────────

function groupByOrder(items: LabItem[]): [string, LabItem[]][] {
  const map = new Map<string, LabItem[]>()
  for (const item of items) {
    const key = item.order_name ?? ''
    if (!map.has(key)) map.set(key, [])
    map.get(key)!.push(item)
  }
  return Array.from(map.entries())
}
