import type { WeeklyGoalAction, WeeklyReview } from '../../api/types'

type Props = {
  review: WeeklyReview
}

export function WeeklyGoalCard({ review }: Props) {
  const goal = review.goal
  const progress = review.progress

  return (
    <div className="grid gap-4">
      {/* 周目标概览 */}
      {goal && (
        <div className="rounded-2xl border border-primary/20 bg-white p-4 shadow-soft">
          <h3 className="font-heading text-lg font-semibold text-primary">{goal.payload.title}</h3>
          <p className="mt-1 text-sm text-slate-600">聚焦: {goal.payload.focus}</p>

          {/* 目标详情 */}
          <TargetCard target={goal.payload.target} />

          {/* 具体任务 */}
          {goal.payload.tasks.length > 0 && (
            <div className="mt-3">
              <div className="text-xs font-medium uppercase tracking-wider text-slate-400">本周任务</div>
              <ul className="mt-1 space-y-1">
                {goal.payload.tasks.map((t, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                    <span className="mt-0.5 text-primary">○</span>
                    {t}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {goal.trace_id && (
            <div className="mt-2 text-[10px] text-slate-400">trace: {goal.trace_id}</div>
          )}
        </div>
      )}

      {/* 进度追踪 */}
      {progress && (
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
          <h4 className="font-heading text-sm font-semibold text-slate-700">进度追踪</h4>
          <div className="mt-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-600">{progress.metric}</span>
              <span className="font-semibold text-primary">{progress.completion_pct.toFixed(0)}%</span>
            </div>
            <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full rounded-full bg-primary transition-all"
                style={{ width: `${Math.min(100, progress.completion_pct)}%` }}
              />
            </div>
            <div className="mt-1 flex justify-between text-xs text-slate-500">
              <span>基线: {progress.baseline} {progress.unit}</span>
              <span>当前: {progress.current} {progress.unit}</span>
              <span>目标: {progress.goal} {progress.unit}</span>
            </div>
          </div>
        </div>
      )}

      {/* 本周亮点 */}
      {review.highlights.length > 0 && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-4">
          <h4 className="font-heading text-sm font-semibold text-emerald-700">本周亮点</h4>
          <ul className="mt-2 space-y-1">
            {review.highlights.map((h, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-emerald-600">
                <span>✦</span>
                {h}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 下周聚焦 */}
      {review.next_focus && (
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <h4 className="font-heading text-sm font-semibold text-slate-700">下周建议聚焦</h4>
          <p className="mt-1 text-sm text-slate-600">{review.next_focus}</p>
        </div>
      )}
    </div>
  )
}

function TargetCard({ target }: { target: WeeklyGoalAction['payload']['target'] }) {
  return (
    <div className="mt-3 grid grid-cols-3 gap-2 rounded-xl bg-primary/5 p-3">
      <div className="text-center">
        <div className="text-xs text-slate-500">基线</div>
        <div className="text-lg font-bold text-slate-700">{target.baseline}</div>
        <div className="text-[10px] text-slate-400">{target.unit}</div>
      </div>
      <div className="text-center">
        <div className="text-xs text-slate-500">目标</div>
        <div className="text-lg font-bold text-primary">{target.goal}</div>
        <div className="text-[10px] text-slate-400">{target.unit}</div>
      </div>
      <div className="text-center">
        <div className="text-xs text-slate-500">周期</div>
        <div className="text-lg font-bold text-slate-700">{target.window_days}</div>
        <div className="text-[10px] text-slate-400">天</div>
      </div>
    </div>
  )
}
