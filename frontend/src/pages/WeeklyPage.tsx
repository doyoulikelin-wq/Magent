import { useWeeklyReview } from '../api/hooks'
import { WeeklyGoalCard } from '../components/agent/WeeklyGoalCard'

export function WeeklyPage() {
  const { data, isLoading, error } = useWeeklyReview()

  if (isLoading) {
    return (
      <div className="grid animate-pulse gap-4">
        <div className="h-48 rounded-2xl bg-slate-200" />
        <div className="h-32 rounded-2xl bg-slate-200" />
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center">
        <div className="text-4xl">🎯</div>
        <h3 className="mt-3 font-heading text-lg font-semibold text-slate-700">等待生成周目标</h3>
        <p className="mt-1 text-sm text-slate-500">
          代理会根据你的历史数据和当前进度自动设定周目标。<br />
          累积足够数据后即可查看。
        </p>
      </div>
    )
  }

  return <WeeklyGoalCard review={data} />
}
