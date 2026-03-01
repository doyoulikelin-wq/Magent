import { useState } from 'react'

import { api } from '../../api/client'
import { useCompletePhoto, useCreateUploadTicket } from '../../api/hooks'
import type { MealPhoto } from '../../api/types'

type Props = {
  onCompleted: (photo: MealPhoto) => void
}

export function MealUploadCard({ onCompleted }: Props) {
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState('')

  const ticket = useCreateUploadTicket()
  const complete = useCompletePhoto()

  const loading = ticket.isPending || complete.isPending

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
      <h3 className="font-heading text-lg font-semibold">上传食物照片</h3>
      <p className="mt-1 text-sm text-slate-500">上传后会自动执行识别、卡路里估算，并推断用餐时间。</p>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <input
          type="file"
          accept="image/*"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="text-sm"
        />
        <button
          disabled={!file || loading}
          className="rounded-lg bg-primary px-3 py-2 text-sm text-white disabled:cursor-not-allowed disabled:bg-slate-300"
          onClick={async () => {
            if (!file) {
              return
            }
            setError('')
            try {
              const tk = await ticket.mutateAsync({ filename: file.name, content_type: file.type || 'image/jpeg' })
              await api.uploadFile(tk.upload_url, file)
              const photo = await complete.mutateAsync({ object_key: tk.object_key })
              onCompleted(photo)
            } catch (err) {
              setError(err instanceof Error ? err.message : '上传失败')
            }
          }}
        >
          {loading ? '处理中...' : '上传并分析'}
        </button>
      </div>

      {error ? <div className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</div> : null}
    </div>
  )
}
