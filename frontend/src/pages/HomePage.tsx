import { useNavigate } from 'react-router-dom'

import { useGlucoseRange, useProactiveMessage } from '../api/hooks'
import { DoctorDog } from '../components/DoctorDog'

export function HomePage({ onLogout }: { onLogout: () => void }) {
  const navigate = useNavigate()
  const { data: range } = useGlucoseRange()
  const { data: proactive } = useProactiveMessage()
  const subjectId = localStorage.getItem('metabodash_subject')

  // Use proactive agent message if available, else static fallback
  const bubbleMessage = proactive?.message
    ?? (range?.count
      ? `你有 ${range.count} 条血糖记录哦，点我聊聊～`
      : '你好呀！点我和我聊聊健康吧～')

  const hasRescue = proactive?.has_rescue ?? false

  return (
    <div className="flex min-h-[calc(100vh-60px)] flex-col items-center justify-center px-4 pb-20">
      {/* Header */}
      <div className="mb-6 text-center">
        <h1 className="font-heading text-2xl font-bold text-slate-800">MetaboDash</h1>
        {subjectId && (
          <span className="mt-1 inline-block rounded-full bg-teal-100 px-3 py-0.5 text-xs font-semibold text-teal-700">
            {subjectId}
          </span>
        )}
      </div>

      {/* Doctor Dog */}
      <DoctorDog
        message={bubbleMessage}
        onBubbleClick={() => navigate('/chat')}
        hasAlert={hasRescue}
      />

      {/* Three main buttons */}
      <div className="mt-8 grid w-full max-w-sm gap-3">
        <button
          onClick={() => navigate('/health')}
          className="flex items-center gap-3 rounded-2xl border border-teal-200 bg-white px-5 py-4 text-left shadow-md transition hover:shadow-lg hover:-translate-y-0.5 active:translate-y-0"
        >
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-teal-50 text-2xl">📊</span>
          <div>
            <div className="font-semibold text-slate-800">健康数据</div>
            <div className="text-xs text-slate-500">体检报告 · 时间轴 · 上传数据</div>
          </div>
        </button>

        <button
          onClick={() => navigate('/glucose')}
          className="flex items-center gap-3 rounded-2xl border border-cyan-200 bg-white px-5 py-4 text-left shadow-md transition hover:shadow-lg hover:-translate-y-0.5 active:translate-y-0"
        >
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-cyan-50 text-2xl">📈</span>
          <div>
            <div className="font-semibold text-slate-800">动态数据</div>
            <div className="text-xs text-slate-500">
              血糖曲线 · 暴食标记{range?.count ? ` · ${range.count}条` : ''}
            </div>
          </div>
        </button>

        <button
          onClick={() => navigate('/food')}
          className="flex items-center gap-3 rounded-2xl border border-orange-200 bg-white px-5 py-4 text-left shadow-md transition hover:shadow-lg hover:-translate-y-0.5 active:translate-y-0"
        >
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-orange-50 text-2xl">🍽️</span>
          <div>
            <div className="font-semibold text-slate-800">吃了什么</div>
            <div className="text-xs text-slate-500">拍照上传 · 卡路里估算 · 食谱记录</div>
          </div>
        </button>
      </div>

      {/* Logout */}
      <button
        onClick={onLogout}
        className="mt-6 text-xs text-slate-400 hover:text-slate-600 transition"
      >
        切换用户
      </button>
    </div>
  )
}
