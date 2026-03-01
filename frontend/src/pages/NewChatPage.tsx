import { FormEvent, useMemo, useState } from 'react'
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import {
  useGlucosePoints,
  useGlucoseRange,
  useRequestPreMealSim,
  useRescueCheck,
  useTodayBriefing,
  useWeeklyReview,
} from '../api/hooks'
import { MessageBubble } from '../components/chat/MessageBubble'
import { useSSEChat } from '../components/chat/useSSEChat'

type DataPanel = 'health' | 'glucose' | 'food' | null

/* ── Agent card types (displayed inline in chat area) ────── */
type AgentCard =
  | { kind: 'briefing'; data: Record<string, unknown> }
  | { kind: 'premeal'; data: Record<string, unknown> }
  | { kind: 'rescue'; data: Record<string, unknown> }
  | { kind: 'weekly'; data: Record<string, unknown> }

export function NewChatPage() {
  const [input, setInput] = useState('')
  const { messages, streaming, error, send } = useSSEChat()
  const [activePanel, setActivePanel] = useState<DataPanel>(null)
  const [agentCards, setAgentCards] = useState<AgentCard[]>([])
  const [showPreMealForm, setShowPreMealForm] = useState(false)
  const [preMealKcal, setPreMealKcal] = useState('500')

  const { data: range } = useGlucoseRange()
  const from = range?.min_ts ?? null
  const to = range?.max_ts ?? null
  const { data: glucosePoints = [] } = useGlucosePoints(from, to)

  const briefingQuery = useTodayBriefing()
  const weeklyQuery = useWeeklyReview()
  const rescueQuery = useRescueCheck()
  const preMealSim = useRequestPreMealSim()

  const miniGlucoseData = useMemo(() => {
    const slice = glucosePoints.slice(-100)
    return slice.map((p) => ({
      ts: new Date(p.ts).getTime(),
      v: p.glucose_mgdl,
    }))
  }, [glucosePoints])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    const text = input.trim()
    if (!text || streaming) return
    setInput('')
    await send(text)
  }

  // Quick action handlers
  function handleBriefing() {
    if (briefingQuery.data) {
      setAgentCards((prev) => [...prev, { kind: 'briefing', data: briefingQuery.data as Record<string, unknown> }])
    } else {
      briefingQuery.refetch().then((res) => {
        if (res.data) setAgentCards((prev) => [...prev, { kind: 'briefing', data: res.data as Record<string, unknown> }])
      })
    }
  }

  function handleRescue() {
    rescueQuery.refetch().then((res) => {
      if (res.data) setAgentCards((prev) => [...prev, { kind: 'rescue', data: res.data as Record<string, unknown> }])
    })
  }

  function handleWeekly() {
    if (weeklyQuery.data) {
      setAgentCards((prev) => [...prev, { kind: 'weekly', data: weeklyQuery.data as Record<string, unknown> }])
    } else {
      weeklyQuery.refetch().then((res) => {
        if (res.data) setAgentCards((prev) => [...prev, { kind: 'weekly', data: res.data as Record<string, unknown> }])
      })
    }
  }

  function handlePreMealSubmit() {
    const kcal = parseFloat(preMealKcal)
    if (isNaN(kcal) || kcal <= 0) return
    preMealSim.mutate(
      { kcal, meal_time: 'now' },
      {
        onSuccess: (data) => {
          setAgentCards((prev) => [...prev, { kind: 'premeal', data: data as unknown as Record<string, unknown> }])
          setShowPreMealForm(false)
        },
      },
    )
  }

  const subjectId = localStorage.getItem('metabodash_subject')

  return (
    <div className="mx-auto flex max-w-lg flex-col pb-24 pt-4 px-4" style={{ height: 'calc(100vh - 60px)' }}>
      {/* Header */}
      <div className="mb-3 flex items-center justify-between">
        <div>
          <h2 className="font-heading text-lg font-bold text-slate-800">🐶 Dr.Dog</h2>
          <p className="text-xs text-slate-500">
            你的健康AI助手{subjectId ? ` · ${subjectId}` : ''}
          </p>
        </div>
      </div>

      {/* Data Panel Buttons */}
      <div className="mb-3 flex gap-2">
        {[
          { key: 'health' as const, icon: '📊', label: '健康数据' },
          { key: 'glucose' as const, icon: '📈', label: '血糖数据' },
          { key: 'food' as const, icon: '🍽️', label: '饮食数据' },
        ].map((p) => (
          <button
            key={p.key}
            onClick={() => setActivePanel(activePanel === p.key ? null : p.key)}
            className={`flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium transition ${
              activePanel === p.key
                ? 'bg-teal-600 text-white shadow-sm'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            <span>{p.icon}</span>
            {p.label}
          </button>
        ))}
      </div>

      {/* Collapsible Data Panel */}
      {activePanel && (
        <div className="mb-3 rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
          {activePanel === 'health' && (
            <div>
              <h4 className="mb-1 text-xs font-semibold text-slate-500">健康概览</h4>
              {range ? (
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="rounded-lg bg-teal-50 p-2 text-center">
                    <div className="text-lg font-bold text-teal-700">{range.count.toLocaleString()}</div>
                    <div className="text-slate-500">数据点</div>
                  </div>
                  <div className="rounded-lg bg-cyan-50 p-2 text-center">
                    <div className="text-lg font-bold text-cyan-700">
                      {range.min_ts && range.max_ts
                        ? Math.ceil(
                            (new Date(range.max_ts).getTime() - new Date(range.min_ts).getTime()) /
                              86400_000,
                          )
                        : 0}
                    </div>
                    <div className="text-slate-500">天数</div>
                  </div>
                </div>
              ) : (
                <div className="text-xs text-slate-400">暂无数据</div>
              )}
            </div>
          )}

          {activePanel === 'glucose' && (
            <div>
              <h4 className="mb-1 text-xs font-semibold text-slate-500">血糖迷你图</h4>
              {miniGlucoseData.length > 0 ? (
                <div className="h-24">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={miniGlucoseData}>
                      <defs>
                        <linearGradient id="miniGluc" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#0f766e" stopOpacity={0.3} />
                          <stop offset="100%" stopColor="#0f766e" stopOpacity={0.02} />
                        </linearGradient>
                      </defs>
                      <XAxis dataKey="ts" hide />
                      <YAxis domain={[40, 250]} hide />
                      <Tooltip
                        labelFormatter={(ts: number) =>
                          new Date(ts).toLocaleString('zh-CN', {
                            month: 'numeric',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })
                        }
                        formatter={(v: number) => [`${v} mg/dL`, '血糖']}
                      />
                      <Area
                        type="monotone"
                        dataKey="v"
                        stroke="#0f766e"
                        fill="url(#miniGluc)"
                        strokeWidth={1.5}
                        dot={false}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="text-xs text-slate-400">暂无血糖数据</div>
              )}
            </div>
          )}

          {activePanel === 'food' && (
            <div>
              <h4 className="mb-1 text-xs font-semibold text-slate-500">近期饮食</h4>
              <div className="space-y-1 text-xs">
                {[
                  { name: '红烧牛肉面', kcal: 520, time: '今天 12:30' },
                  { name: '煎蛋 + 牛奶', kcal: 380, time: '今天 08:15' },
                  { name: '宫保鸡丁', kcal: 650, time: '昨天 18:45' },
                ].map((f, i) => (
                  <div key={i} className="flex items-center justify-between rounded-lg bg-slate-50 px-2 py-1.5">
                    <span className="text-slate-700">{f.name}</span>
                    <span className="text-slate-500">{f.kcal} kcal · {f.time}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Agent Quick Actions ── */}
      <div className="mb-3 flex flex-wrap gap-2">
        <button
          onClick={handleBriefing}
          className="rounded-full bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-700 ring-1 ring-amber-200 transition hover:bg-amber-100"
        >
          🌤️ 今日简报
        </button>
        <button
          onClick={() => setShowPreMealForm(!showPreMealForm)}
          className="rounded-full bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-700 ring-1 ring-blue-200 transition hover:bg-blue-100"
        >
          🍽️ 吃前预演
        </button>
        <button
          onClick={handleRescue}
          className="rounded-full bg-rose-50 px-3 py-1.5 text-xs font-medium text-rose-700 ring-1 ring-rose-200 transition hover:bg-rose-100"
        >
          🚨 血糖急救
        </button>
        <button
          onClick={handleWeekly}
          className="rounded-full bg-violet-50 px-3 py-1.5 text-xs font-medium text-violet-700 ring-1 ring-violet-200 transition hover:bg-violet-100"
        >
          📊 周复盘
        </button>
      </div>

      {/* Pre-meal sim input form */}
      {showPreMealForm && (
        <div className="mb-3 rounded-xl border border-blue-200 bg-blue-50/50 p-3">
          <p className="mb-2 text-xs font-semibold text-blue-700">🍽️ 吃前预演 — 输入预计热量</p>
          <div className="flex items-center gap-2">
            <input
              type="number"
              value={preMealKcal}
              onChange={(e) => setPreMealKcal(e.target.value)}
              className="w-24 rounded-lg border border-blue-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
              placeholder="kcal"
              min="100"
              max="3000"
            />
            <span className="text-xs text-slate-500">kcal</span>
            <button
              onClick={handlePreMealSubmit}
              disabled={preMealSim.isPending}
              className="ml-auto rounded-lg bg-blue-600 px-4 py-1.5 text-xs font-medium text-white transition hover:bg-blue-700 disabled:bg-slate-300"
            >
              {preMealSim.isPending ? '预测中...' : '开始预演'}
            </button>
          </div>
        </div>
      )}

      {/* Messages + Agent Cards */}
      <div className="flex-1 space-y-3 overflow-y-auto rounded-2xl border border-slate-200 bg-white p-4">
        {messages.length === 0 && agentCards.length === 0 && (
          <div className="flex flex-col items-center justify-center py-8 text-slate-400">
            <span className="text-4xl">🐶</span>
            <p className="mt-2 text-sm">你好，我是 Dr.Dog！</p>
            <p className="text-xs">点上方按钮获取今日简报、吃前预演或周复盘</p>
            <p className="text-xs">也可以直接问我关于血糖、饮食或健康的问题</p>
          </div>
        )}

        {/* Interleave agent cards and messages chronologically */}
        {agentCards.map((card, idx) => (
          <AgentCardView key={`agent-${idx}`} card={card} />
        ))}
        {messages.map((m) => (
          <MessageBubble key={m.id} role={m.role} content={m.content} />
        ))}
      </div>

      {/* Input */}
      <form onSubmit={onSubmit} className="mt-3 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          className="flex-1 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm focus:border-teal-500 focus:outline-none"
          placeholder="输入你的问题..."
        />
        <button
          type="submit"
          disabled={streaming}
          className="rounded-xl bg-teal-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-teal-700 disabled:bg-slate-300"
        >
          {streaming ? '...' : '发送'}
        </button>
      </form>
      {error && <div className="mt-1 text-xs text-red-500">{error}</div>}
    </div>
  )
}

/* ═════════════════════════════════════════════════════════════
   Agent Card Rendering Components
   ═════════════════════════════════════════════════════════════ */

function AgentCardView({ card }: { card: AgentCard }) {
  switch (card.kind) {
    case 'briefing':
      return <BriefingCard data={card.data} />
    case 'premeal':
      return <PreMealCard data={card.data} />
    case 'rescue':
      return <RescueCard data={card.data} />
    case 'weekly':
      return <WeeklyCard data={card.data} />
  }
}

/* ── 今日简报卡片 ── */
function BriefingCard({ data }: { data: Record<string, unknown> }) {
  const greeting = (data.greeting as string) || '今日代谢天气'
  const gs = (data.glucose_status as Record<string, unknown>) || {}
  const riskWindows = (data.risk_windows as Array<Record<string, unknown>>) || []
  const goals = (data.today_goals as string[]) || []

  return (
    <div className="rounded-xl border border-amber-200 bg-gradient-to-br from-amber-50 to-orange-50 p-4 shadow-sm">
      <div className="mb-2 text-sm font-semibold text-amber-800">🌤️ 今日代谢天气</div>
      <p className="mb-3 text-sm text-slate-700">{greeting}</p>

      {/* Glucose status row */}
      {gs.current_mgdl != null && (
        <div className="mb-2 flex gap-3 text-xs">
          <span className="rounded bg-white/80 px-2 py-1 text-slate-600">
            当前 <b className="text-slate-800">{String(gs.current_mgdl)} mg/dL</b>
          </span>
          {gs.tir_24h != null && (
            <span className="rounded bg-white/80 px-2 py-1 text-slate-600">
              TIR <b className="text-teal-700">{String(gs.tir_24h)}%</b>
            </span>
          )}
          {gs.cv_24h != null && (
            <span className="rounded bg-white/80 px-2 py-1 text-slate-600">
              CV <b className="text-cyan-700">{String(gs.cv_24h)}%</b>
            </span>
          )}
        </div>
      )}

      {/* Risk windows */}
      {riskWindows.length > 0 && (
        <div className="mb-2">
          <p className="text-xs font-medium text-amber-700">⚠️ 风险时段</p>
          {riskWindows.map((rw, i) => (
            <p key={i} className="text-xs text-slate-600">
              {String(rw.start)} - {String(rw.end)}（{String(rw.risk)}）· {String(rw.reason || '')}
            </p>
          ))}
        </div>
      )}

      {/* Goals */}
      {goals.length > 0 && (
        <div>
          <p className="text-xs font-medium text-amber-700">🎯 今日目标</p>
          {goals.map((g, i) => (
            <p key={i} className="text-xs text-slate-600">• {g}</p>
          ))}
        </div>
      )}
    </div>
  )
}

/* ── 吃前预演卡片 ── */
function PreMealCard({ data }: { data: Record<string, unknown> }) {
  const title = (data.title as string) || '吃前预演'
  const pred = (data.prediction as Record<string, unknown>) || {}
  const alts = (data.alternatives as Array<Record<string, unknown>>) || []

  return (
    <div className="rounded-xl border border-blue-200 bg-gradient-to-br from-blue-50 to-indigo-50 p-4 shadow-sm">
      <div className="mb-2 text-sm font-semibold text-blue-800">🍽️ {title}</div>

      <div className="mb-3 grid grid-cols-3 gap-2 text-center text-xs">
        <div className="rounded-lg bg-white/80 p-2">
          <div className="text-lg font-bold text-blue-700">{String(pred.peak_glucose ?? '--')}</div>
          <div className="text-slate-500">预测峰值 mg/dL</div>
        </div>
        <div className="rounded-lg bg-white/80 p-2">
          <div className="text-lg font-bold text-blue-700">+{String(pred.peak_delta ?? '--')}</div>
          <div className="text-slate-500">升幅</div>
        </div>
        <div className="rounded-lg bg-white/80 p-2">
          <div className="text-lg font-bold text-blue-700">{String(pred.time_to_peak_min ?? '--')}'</div>
          <div className="text-slate-500">达峰时间</div>
        </div>
      </div>

      {/* Confidence */}
      {pred.confidence != null && (
        <p className="mb-2 text-xs text-slate-500">
          预测置信度: {(Number(pred.confidence) * 100).toFixed(0)}%
        </p>
      )}

      {/* Alternatives */}
      {alts.length > 0 && (
        <div>
          <p className="mb-1 text-xs font-medium text-blue-700">💡 替代方案</p>
          {alts.map((a, i) => (
            <div key={i} className="flex items-center justify-between rounded-lg bg-white/70 px-2 py-1.5 mb-1 text-xs">
              <span className="text-slate-700">{String(a.label)}</span>
              <span className={`font-semibold ${Number(a.expected_delta_peak) < 0 ? 'text-green-600' : 'text-red-500'}`}>
                {Number(a.expected_delta_peak) > 0 ? '+' : ''}{String(a.expected_delta_peak)} mg/dL
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

/* ── 血糖急救卡片 ── */
function RescueCard({ data }: { data: Record<string, unknown> }) {
  const title = (data.title as string) || '血糖检查'
  const riskLevel = data.risk_level as string | undefined
  const steps = (data.steps as Array<Record<string, unknown>>) || []
  const triggers = (data.trigger_evidence as string[]) || []
  const noRescue = data.type === 'no_rescue'

  if (noRescue) {
    return (
      <div className="rounded-xl border border-green-200 bg-gradient-to-br from-green-50 to-emerald-50 p-4 shadow-sm">
        <div className="text-sm font-semibold text-green-800">✅ 血糖平稳</div>
        <p className="mt-1 text-xs text-slate-600">{(data.message as string) || '无需补救'}</p>
      </div>
    )
  }

  return (
    <div className={`rounded-xl border p-4 shadow-sm ${
      riskLevel === 'high'
        ? 'border-red-300 bg-gradient-to-br from-red-50 to-rose-50'
        : 'border-orange-200 bg-gradient-to-br from-orange-50 to-amber-50'
    }`}>
      <div className={`mb-2 text-sm font-semibold ${riskLevel === 'high' ? 'text-red-800' : 'text-orange-800'}`}>
        {title}
      </div>

      {/* Trigger evidence */}
      {triggers.length > 0 && (
        <div className="mb-2 space-y-0.5">
          {triggers.map((t, i) => (
            <p key={i} className="text-xs text-slate-600">⚡ {t}</p>
          ))}
        </div>
      )}

      {/* Steps */}
      {steps.length > 0 && (
        <div>
          <p className="mb-1 text-xs font-medium text-amber-700">🏃 建议操作</p>
          {steps.map((s, i) => (
            <div key={i} className="mb-1 flex items-center gap-2 rounded-lg bg-white/70 px-2 py-1.5 text-xs">
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-amber-200 text-[10px] font-bold text-amber-800">
                {i + 1}
              </span>
              <span className="text-slate-700">{String(s.label)}</span>
              {s.duration_min != null && (
                <span className="ml-auto text-slate-400">{Number(s.duration_min)} 分钟</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

/* ── 周复盘卡片 ── */
function WeeklyCard({ data }: { data: Record<string, unknown> }) {
  const title = (data.title as string) || '本周复盘'
  const highlights = (data.highlights as string[]) || []
  const nextFocus = data.next_focus as string | undefined
  const target = data.target as Record<string, unknown> | undefined
  const tasks = (data.tasks as string[]) || []

  return (
    <div className="rounded-xl border border-violet-200 bg-gradient-to-br from-violet-50 to-purple-50 p-4 shadow-sm">
      <div className="mb-2 text-sm font-semibold text-violet-800">{title}</div>

      {/* Highlights */}
      {highlights.length > 0 && (
        <div className="mb-2">
          {highlights.map((h, i) => (
            <p key={i} className="text-xs text-slate-600">{h}</p>
          ))}
        </div>
      )}

      {/* Target */}
      {target && (
        <div className="mb-2 rounded-lg bg-white/70 p-2 text-xs">
          <p className="font-medium text-violet-700">🎯 下周目标: {nextFocus}</p>
          <p className="text-slate-500">
            {String(target.metric)}: {String(target.baseline)}{String(target.unit)} → {String(target.goal)}{String(target.unit)}
          </p>
        </div>
      )}

      {/* Tasks */}
      {tasks.length > 0 && (
        <div>
          <p className="mb-1 text-xs font-medium text-violet-700">📋 行动清单</p>
          {tasks.map((t, i) => (
            <p key={i} className="text-xs text-slate-600">• {t}</p>
          ))}
        </div>
      )}
    </div>
  )
}
