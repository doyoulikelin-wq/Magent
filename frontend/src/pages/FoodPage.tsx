import { useState } from 'react'

/**
 * FoodPage – 吃了什么
 *
 * 上半部分：相机拍照区域（占位演示）
 * 下半部分：历史食谱列表（卡路里 + 时间戳）
 */

type FoodRecord = {
  id: string
  ts: string
  name: string
  kcal: number
}

// 演示数据（后续由 API 替换）
const demoHistory: FoodRecord[] = [
  { id: '1', ts: '2025-02-28T12:30:00', name: '红烧牛肉面', kcal: 520 },
  { id: '2', ts: '2025-02-28T08:15:00', name: '煎蛋 + 牛奶 + 全麦面包', kcal: 380 },
  { id: '3', ts: '2025-02-27T18:45:00', name: '宫保鸡丁 + 米饭', kcal: 650 },
  { id: '4', ts: '2025-02-27T12:00:00', name: '番茄鸡蛋汤面', kcal: 420 },
  { id: '5', ts: '2025-02-27T07:50:00', name: '豆浆 + 油条', kcal: 350 },
  { id: '6', ts: '2025-02-26T19:30:00', name: '火锅（多人聚餐）', kcal: 1200 },
  { id: '7', ts: '2025-02-26T12:20:00', name: '沙拉 + 鸡胸肉', kcal: 310 },
]

export function FoodPage() {
  const [cameraActive, setCameraActive] = useState(false)
  const [capturedImage, setCapturedImage] = useState<string | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [analysisResult, setAnalysisResult] = useState<{ name: string; kcal: number } | null>(null)

  function handleCapture() {
    setCameraActive(false)
    // Simulated captured image (placeholder)
    setCapturedImage('captured')
    // Simulate AI analysis
    setAnalyzing(true)
    setTimeout(() => {
      setAnalyzing(false)
      setAnalysisResult({ name: '红烧排骨 + 炒青菜 + 米饭', kcal: 680 })
    }, 2000)
  }

  function resetCamera() {
    setCapturedImage(null)
    setAnalysisResult(null)
    setCameraActive(false)
  }

  return (
    <div className="mx-auto max-w-lg px-4 pb-24 pt-6">
      <h2 className="mb-4 font-heading text-xl font-bold text-slate-800">吃了什么</h2>

      {/* ── Camera Section ──────────────────────────────── */}
      <div className="mb-6 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        {!capturedImage ? (
          <div className="flex flex-col items-center justify-center bg-slate-900 py-16">
            {cameraActive ? (
              <>
                {/* Simulated viewfinder */}
                <div className="mb-4 flex h-40 w-56 items-center justify-center rounded-xl border-2 border-dashed border-white/40">
                  <div className="text-center text-white/60">
                    <div className="text-4xl">🍽️</div>
                    <div className="mt-1 text-xs">将食物放入框内</div>
                  </div>
                </div>
                <button
                  onClick={handleCapture}
                  className="flex h-16 w-16 items-center justify-center rounded-full border-4 border-white bg-white/20 transition hover:bg-white/30"
                >
                  <div className="h-12 w-12 rounded-full bg-white" />
                </button>
              </>
            ) : (
              <>
                <div className="mb-3 text-5xl">📷</div>
                <p className="mb-4 text-sm text-white/70">拍照识别食物和卡路里</p>
                <button
                  onClick={() => setCameraActive(true)}
                  className="rounded-xl bg-teal-500 px-6 py-2.5 text-sm font-medium text-white transition hover:bg-teal-600"
                >
                  打开相机
                </button>
              </>
            )}
          </div>
        ) : (
          <div className="p-4">
            {/* Captured result */}
            <div className="flex items-center gap-3 rounded-xl bg-slate-50 p-3">
              <div className="flex h-16 w-16 items-center justify-center rounded-xl bg-slate-200 text-3xl">
                🍱
              </div>
              <div className="flex-1">
                {analyzing ? (
                  <>
                    <div className="h-4 w-32 animate-pulse rounded bg-slate-200" />
                    <div className="mt-2 h-3 w-20 animate-pulse rounded bg-slate-200" />
                    <p className="mt-1 text-xs text-slate-500">AI 识别中...</p>
                  </>
                ) : analysisResult ? (
                  <>
                    <div className="font-medium text-slate-800">{analysisResult.name}</div>
                    <div className="mt-0.5 text-sm">
                      预估 <span className="font-bold text-orange-600">{analysisResult.kcal}</span>{' '}
                      kcal
                    </div>
                  </>
                ) : null}
              </div>
            </div>

            {analysisResult && (
              <div className="mt-3 flex gap-2">
                <button
                  onClick={resetCamera}
                  className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-600"
                >
                  重新拍
                </button>
                <button
                  onClick={resetCamera}
                  className="flex-1 rounded-lg bg-teal-600 px-3 py-2 text-sm font-medium text-white"
                >
                  确认记录
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Food History ────────────────────────────────── */}
      <div>
        <h3 className="mb-3 text-sm font-semibold text-slate-600">历史食谱</h3>
        <div className="space-y-2">
          {demoHistory.map((food) => {
            const isBinge = food.kcal >= 800
            return (
              <div
                key={food.id}
                className={`flex items-center justify-between rounded-xl border p-3 ${
                  isBinge
                    ? 'border-rose-200 bg-rose-50'
                    : 'border-slate-200 bg-white'
                }`}
              >
                <div>
                  <div className="text-sm font-medium text-slate-800">
                    {food.name}
                    {isBinge && (
                      <span className="ml-1.5 rounded bg-rose-100 px-1.5 py-0.5 text-[10px] font-semibold text-rose-600">
                        暴食
                      </span>
                    )}
                  </div>
                  <div className="mt-0.5 text-xs text-slate-400">
                    {new Date(food.ts).toLocaleString('zh-CN', {
                      month: 'numeric',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </div>
                </div>
                <div
                  className={`text-sm font-bold ${isBinge ? 'text-rose-600' : 'text-slate-700'}`}
                >
                  {food.kcal} kcal
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
