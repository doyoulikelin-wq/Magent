import { useState } from 'react'

import type { AgentAction } from '../../api/types'

type Props = {
  actions: AgentAction[]
}

export function EvidenceDrawer({ actions }: Props) {
  const [expandedId, setExpandedId] = useState<string | null>(null)

  if (actions.length === 0) {
    return (
      <div className="rounded-xl bg-slate-50 p-4 text-center text-sm text-slate-500">
        暂无可追溯的动作记录
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {actions.map((action) => {
        const expanded = expandedId === action.id
        return (
          <div
            key={action.id}
            className="rounded-2xl border border-slate-200 bg-white shadow-soft transition-all"
          >
            {/* 摘要行 */}
            <button
              onClick={() => setExpandedId(expanded ? null : action.id)}
              className="flex w-full items-center justify-between px-4 py-3 text-left"
            >
              <div className="flex items-center gap-2">
                <ActionTypeIcon type={action.action_type} />
                <span className="text-sm font-medium text-slate-900">{action.payload.title}</span>
                <StatusBadge status={action.status} />
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400">
                  {new Date(action.created_ts).toLocaleString('zh-CN', {
                    month: 'numeric',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
                <span className="text-slate-400">{expanded ? '▲' : '▼'}</span>
              </div>
            </button>

            {/* 展开详情 */}
            {expanded && (
              <div className="border-t border-slate-100 px-4 py-3">
                {/* 证据信号 */}
                <Section title="触发信号">
                  {action.reason_evidence.signals?.map((s, i) => (
                    <span key={i} className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">{s}</span>
                  )) ?? <span className="text-xs text-slate-400">无信号</span>}
                </Section>

                {action.reason_evidence.summary && (
                  <Section title="摘要">
                    <p className="text-sm text-slate-600">{action.reason_evidence.summary}</p>
                  </Section>
                )}

                {action.reason_evidence.window && (
                  <Section title="数据窗口">
                    <span className="text-sm text-slate-600">{action.reason_evidence.window}</span>
                  </Section>
                )}

                {/* 数据来源层级 */}
                <Section title="数据来源层级">
                  <div className="flex gap-2">
                    <SourceLevel label="个人实时" active />
                    <SourceLevel label="个人历史" active={!!action.reason_evidence.window} />
                    <SourceLevel label="队列先验" active={false} />
                  </div>
                </Section>

                {/* 元数据 */}
                <div className="mt-2 flex flex-wrap gap-3 text-[10px] text-slate-400">
                  <span>version: {action.payload_version}</span>
                  {action.trace_id && <span>trace: {action.trace_id}</span>}
                  {action.error_code && <span>error: {action.error_code}</span>}
                  {action.priority && <span>priority: {action.priority}</span>}
                </div>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mt-2">
      <div className="text-xs font-medium uppercase tracking-wider text-slate-400">{title}</div>
      <div className="mt-1 flex flex-wrap gap-1">{children}</div>
    </div>
  )
}

function ActionTypeIcon({ type }: { type: string }) {
  const icons: Record<string, string> = {
    pre_meal_sim: '🔮',
    rescue: '🚑',
    daily_plan: '📋',
    weekly_goal: '🎯',
  }
  return <span className="text-base">{icons[type] ?? '📄'}</span>
}

function StatusBadge({ status }: { status: string }) {
  if (status === 'valid') return null
  const colors = status === 'degraded'
    ? 'bg-amber-100 text-amber-700'
    : 'bg-red-100 text-red-700'
  return (
    <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium ${colors}`}>
      {status === 'degraded' ? '已安全降级' : '无效'}
    </span>
  )
}

function SourceLevel({ label, active }: { label: string; active: boolean }) {
  return (
    <div className={`rounded-lg border px-2 py-1 text-xs ${
      active ? 'border-primary/30 bg-primary/5 text-primary' : 'border-slate-200 bg-slate-50 text-slate-400'
    }`}>
      {label}
    </div>
  )
}
