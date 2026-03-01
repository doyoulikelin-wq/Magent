import { useTodayBriefing } from '../api/hooks'
import { TodayBriefingCard } from '../components/agent/TodayBriefingCard'

export function TodayPage() {
  const { data, isLoading, error } = useTodayBriefing()

  if (isLoading) {
    return <Skeleton />
  }

  if (error || !data) {
    return (
      <div className="grid gap-4">
        <EmptyState />
      </div>
    )
  }

  return <TodayBriefingCard data={data} />
}

function Skeleton() {
  return (
    <div className="grid animate-pulse gap-4">
      <div className="h-20 rounded-2xl bg-slate-200" />
      <div className="h-40 rounded-2xl bg-slate-200" />
      <div className="h-28 rounded-2xl bg-slate-200" />
    </div>
  )
}

function EmptyState() {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center">
      <div className="text-4xl">📋</div>
      <h3 className="mt-3 font-heading text-lg font-semibold text-slate-700">等待代理生成简报</h3>
      <p className="mt-1 text-sm text-slate-500">
        代理会在获取到足够数据后自动生成你的每日简报。<br />
        可以先到 <span className="font-medium text-primary">历史数据 → 健康数据</span> 导入血糖文件。
      </p>
    </div>
  )
}
