import type { MealPhoto } from '../../api/types'

type Props = {
  photos: MealPhoto[]
}

export function MealsTable({ photos }: Props) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
      <h3 className="mb-3 font-heading text-lg font-semibold text-slate-900">餐图处理历史</h3>
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-slate-500">
              <th className="px-2 py-2">上传时间</th>
              <th className="px-2 py-2">状态</th>
              <th className="px-2 py-2">估算 kcal</th>
              <th className="px-2 py-2">置信度</th>
            </tr>
          </thead>
          <tbody>
            {photos.map((photo) => (
              <tr key={photo.id} className="border-b border-slate-100">
                <td className="px-2 py-2">{new Date(photo.uploaded_at).toLocaleString()}</td>
                <td className="px-2 py-2">{photo.status}</td>
                <td className="px-2 py-2">{photo.calorie_estimate_kcal ?? '--'}</td>
                <td className="px-2 py-2">{photo.confidence == null ? '--' : `${Math.round(photo.confidence * 100)}%`}</td>
              </tr>
            ))}
            {photos.length === 0 ? (
              <tr>
                <td className="px-2 py-4 text-slate-500" colSpan={4}>
                  暂无餐图记录
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  )
}
