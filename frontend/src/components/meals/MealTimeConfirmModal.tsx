import { useEffect, useMemo, useState } from 'react'

import type { MealPhoto } from '../../api/types'

type Props = {
  photo: MealPhoto | null
  onClose: () => void
  onConfirm: (payload: { meal_ts: string; kcal: number; tags: string[]; meal_ts_source: string; notes?: string }) => Promise<void>
}

function toDateTimeInputValue(value: string): string {
  const dt = new Date(value)
  const offset = dt.getTimezoneOffset()
  const local = new Date(dt.getTime() - offset * 60_000)
  return local.toISOString().slice(0, 16)
}

export function MealTimeConfirmModal({ photo, onClose, onConfirm }: Props) {
  const initialTs = useMemo(() => {
    if (photo?.suggested_meal_ts) {
      return toDateTimeInputValue(photo.suggested_meal_ts)
    }
    return toDateTimeInputValue(new Date().toISOString())
  }, [photo])

  const [mealTs, setMealTs] = useState(initialTs)
  const [kcal, setKcal] = useState(photo?.calorie_estimate_kcal ?? 500)
  const [tags, setTags] = useState(('items' in (photo?.vision_json ?? {}) ? ['photo_estimated'] : []).join(','))
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    setMealTs(initialTs)
    setKcal(photo?.calorie_estimate_kcal ?? 500)
    setTags(('items' in (photo?.vision_json ?? {}) ? ['photo_estimated'] : []).join(','))
  }, [initialTs, photo])

  if (!photo) {
    return null
  }

  const mealSource = photo.suggested_meal_ts ? 'inferred_from_glucose' : 'uploaded_at'

  return (
    <div className="fixed inset-0 z-30 flex items-center justify-center bg-slate-900/40 p-4">
      <div className="w-full max-w-lg rounded-2xl bg-white p-5 shadow-2xl">
        <h3 className="font-heading text-xl font-semibold">确认用餐事件</h3>
        <p className="mt-1 text-sm text-slate-500">系统已给出估算，你可以直接修正时间和热量。</p>

        <div className="mt-4 grid gap-3">
          <label className="grid gap-1 text-sm">
            用餐时间
            <input
              type="datetime-local"
              className="rounded-lg border border-slate-300 px-3 py-2"
              value={mealTs}
              onChange={(e) => setMealTs(e.target.value)}
            />
          </label>

          <label className="grid gap-1 text-sm">
            热量（kcal）
            <input
              type="number"
              className="rounded-lg border border-slate-300 px-3 py-2"
              value={kcal}
              onChange={(e) => setKcal(Number(e.target.value))}
            />
          </label>

          <label className="grid gap-1 text-sm">
            标签（逗号分隔）
            <input
              className="rounded-lg border border-slate-300 px-3 py-2"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
            />
          </label>
        </div>

        <div className="mt-5 flex justify-end gap-2">
          <button className="rounded-lg border px-3 py-2" onClick={onClose} disabled={saving}>
            取消
          </button>
          <button
            className="rounded-lg bg-primary px-3 py-2 text-white"
            disabled={saving}
            onClick={async () => {
              setSaving(true)
              try {
                await onConfirm({
                  meal_ts: new Date(mealTs).toISOString(),
                  kcal,
                  tags: tags
                    .split(',')
                    .map((x) => x.trim())
                    .filter(Boolean),
                  meal_ts_source: mealSource,
                })
              } finally {
                setSaving(false)
              }
            }}
          >
            {saving ? '保存中...' : '确认创建 Meal'}
          </button>
        </div>
      </div>
    </div>
  )
}
