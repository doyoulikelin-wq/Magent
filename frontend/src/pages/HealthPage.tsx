import { useState } from 'react'

import {
  useGlucosePoints,
  useGlucoseRange,
  useGlucoseSamples,
  useHealthDashboard,
  useImportSampleGlucose,
  useMealSamples,
  useRunBatchETL,
} from '../api/hooks'
import { GlucoseChart } from '../components/health/GlucoseChart'
import { MetricsCards } from '../components/health/MetricsCards'

export function HealthPage() {
  const { data, isLoading, error } = useHealthDashboard()
  const { data: glucoseSamples = [] } = useGlucoseSamples()
  const { data: mealSamples = [] } = useMealSamples()
  const { data: glucoseRange } = useGlucoseRange()
  const importSample = useImportSampleGlucose()
  const batchETL = useRunBatchETL()

  // Fetch real time-series points when we know the data range
  const fromTs = glucoseRange?.min_ts ?? null
  const toTs = glucoseRange?.max_ts ?? null
  const { data: glucosePoints = [] } = useGlucosePoints(fromTs, toTs)

  const [selectedGlucose, setSelectedGlucose] = useState('')
  const [importResult, setImportResult] = useState<{ inserted: number; skipped: number } | null>(null)
  const [batchResult, setBatchResult] = useState<string | null>(null)

  if (isLoading) {
    return <div className="rounded-xl bg-white p-4">加载中...</div>
  }
  if (error || !data) {
    return <div className="rounded-xl bg-red-50 p-4 text-red-600">加载健康数据失败</div>
  }

  return (
    <div className="grid gap-4">
      {/* ── 血糖 CSV 导入 ── */}
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
        <h3 className="font-heading text-lg font-semibold">导入血糖数据</h3>
        <p className="mt-1 text-sm text-slate-500">
          从已有 {glucoseSamples.length} 份 Clarity 导出文件中选择一份导入。
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <select
            value={selectedGlucose}
            onChange={(e) => { setSelectedGlucose(e.target.value); setImportResult(null) }}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
          >
            <option value="">-- 选择血糖文件 --</option>
            {glucoseSamples.map((f) => (
              <option key={f.filename} value={f.filename}>
                {f.subject_id ?? f.filename} ({f.size_kb} KB)
              </option>
            ))}
          </select>
          <button
            className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white disabled:bg-slate-300"
            disabled={!selectedGlucose || importSample.isPending}
            onClick={async () => {
              if (!selectedGlucose) return
              const res = await importSample.mutateAsync(selectedGlucose)
              setImportResult({ inserted: res.inserted, skipped: res.skipped })
            }}
          >
            {importSample.isPending ? '导入中...' : '导入'}
          </button>
        </div>
        {importResult && (
          <div className="mt-2 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
            ✅ 成功导入 {importResult.inserted} 条，跳过 {importResult.skipped} 条
          </div>
        )}
        {importSample.isError && (
          <div className="mt-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
            导入失败: {(importSample.error as Error)?.message ?? '未知错误'}
          </div>
        )}
      </div>

      {/* ── 批量 ETL（饮食 + 特征） ── */}
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
        <h3 className="font-heading text-lg font-semibold">批量导入饮食 & 特征数据</h3>
        <p className="mt-1 text-sm text-slate-500">
          一键导入 data/ 下所有已有数据
          {mealSamples.length > 0 && (
            <span className="ml-1">
              ({mealSamples.map((f) => f.filename).join(', ')})
            </span>
          )}
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button
            className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white disabled:bg-slate-300"
            disabled={batchETL.isPending}
            onClick={async () => {
              setBatchResult(null)
              const res = await batchETL.mutateAsync({ skip_glucose: true, skip_features: true })
              setBatchResult(JSON.stringify(res, null, 2))
            }}
          >
            {batchETL.isPending ? '执行中...' : '导入饮食数据'}
          </button>
          <button
            className="rounded-lg border border-primary px-4 py-2 text-sm font-medium text-primary disabled:border-slate-300 disabled:text-slate-400"
            disabled={batchETL.isPending}
            onClick={async () => {
              setBatchResult(null)
              const res = await batchETL.mutateAsync({})
              setBatchResult(JSON.stringify(res, null, 2))
            }}
          >
            {batchETL.isPending ? '执行中...' : '全量 ETL (血糖+饮食+特征)'}
          </button>
        </div>
        {batchResult && (
          <pre className="mt-2 max-h-40 overflow-auto rounded-lg bg-slate-50 p-3 text-xs text-slate-700">
            {batchResult}
          </pre>
        )}
        {batchETL.isError && (
          <div className="mt-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
            批量导入失败: {(batchETL.error as Error)?.message ?? '未知错误'}
          </div>
        )}
      </div>

      <MetricsCards data={data} />

      <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
        <GlucoseChart
          points={glucosePoints}
          rangeMin={glucoseRange?.min_ts ?? null}
          rangeMax={glucoseRange?.max_ts ?? null}
        />

        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
          <h3 className="font-heading text-lg font-semibold">今日用餐</h3>
          <div className="mt-3 space-y-2">
            {data.meals_today.map((meal) => (
              <div key={meal.id} className="rounded-lg border border-slate-200 p-3">
                <div className="text-sm font-medium text-slate-900">{new Date(meal.ts).toLocaleTimeString()}</div>
                <div className="text-sm text-slate-600">
                  {meal.kcal} kcal · {meal.tags.join(', ') || '无标签'}
                </div>
              </div>
            ))}
            {data.meals_today.length === 0 ? <div className="text-sm text-slate-500">今天还没有记录用餐</div> : null}
          </div>
        </div>
      </div>
    </div>
  )
}
