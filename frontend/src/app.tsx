import { useState } from 'react'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'

import { clearToken, getToken, setToken } from './api/client'
import { useSubjectLogin, useSubjects } from './api/hooks'
import type { SubjectInfo } from './api/types'
import { AppRoutes } from './routes'

const queryClient = new QueryClient()

/* ── Subject Picker Login ──────────────────────────────────── */

function SubjectCard({
  subject,
  onClick,
  disabled,
}: {
  subject: SubjectInfo
  onClick: () => void
  disabled: boolean
}) {
  const isCGM = subject.cohort === 'cgm'
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={[
        'relative flex flex-col items-center gap-1 rounded-2xl border-2 px-4 py-3 text-sm font-medium transition-all',
        'hover:shadow-lg hover:-translate-y-0.5 active:translate-y-0',
        'disabled:opacity-50 disabled:cursor-wait',
        isCGM
          ? 'border-teal-300 bg-teal-50 text-teal-800 hover:border-teal-500'
          : 'border-orange-300 bg-orange-50 text-orange-800 hover:border-orange-500',
      ].join(' ')}
    >
      <span className="text-lg font-bold">{subject.subject_id}</span>
      <span className="flex items-center gap-1.5 text-xs opacity-70">
        {subject.has_glucose && <span>📈 血糖</span>}
        {subject.has_meals && <span>🍽️ 饮食</span>}
      </span>
    </button>
  )
}

function AuthPanel({ onAuthed }: { onAuthed: () => void }) {
  const { data: subjects, isLoading: loadingList, error: listError } = useSubjects()
  const loginMut = useSubjectLogin()
  const [loggingIn, setLoggingIn] = useState<string | null>(null)
  const [error, setError] = useState('')

  async function handlePick(sid: string) {
    setError('')
    setLoggingIn(sid)
    try {
      const res = await loginMut.mutateAsync(sid)
      setToken(res.access_token)
      // Store subject_id so sidebar can show it
      localStorage.setItem('metabodash_subject', sid)
      onAuthed()
    } catch (err) {
      setError(err instanceof Error ? err.message : '登录失败')
    } finally {
      setLoggingIn(null)
    }
  }

  const cgmSubjects = subjects?.filter((s) => s.cohort === 'cgm') ?? []
  const liverSubjects = subjects?.filter((s) => s.cohort === 'liver') ?? []

  return (
    <div className="min-h-screen bg-gradient-to-br from-teal-100 via-cyan-100 to-orange-100 p-6">
      <div className="mx-auto mt-8 max-w-4xl rounded-3xl border border-white/60 bg-white/80 p-8 shadow-2xl backdrop-blur">
        <h1 className="font-heading text-3xl font-bold text-slate-900">MetaboDash</h1>
        <p className="mt-1 text-sm text-slate-600">选择受试者登录，查看对应的健康数据</p>

        {error && <div className="mt-4 rounded-lg bg-red-50 px-4 py-2 text-sm text-red-600">{error}</div>}

        {loadingList && <p className="mt-8 text-center text-slate-500">加载受试者列表...</p>}
        {listError && (
          <p className="mt-8 text-center text-red-500">
            加载失败: {listError instanceof Error ? listError.message : '未知错误'}
          </p>
        )}

        {/* CGM cohort */}
        {cgmSubjects.length > 0 && (
          <section className="mt-6">
            <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold text-teal-700">
              <span className="inline-block h-3 w-3 rounded-full bg-teal-400" />
              CGM 受试者
              <span className="text-xs font-normal text-slate-500">({cgmSubjects.length} 人 · 含饮食数据)</span>
            </h2>
            <div className="grid grid-cols-4 gap-3 sm:grid-cols-6 md:grid-cols-8 lg:grid-cols-10">
              {cgmSubjects.map((s) => (
                <SubjectCard
                  key={s.subject_id}
                  subject={s}
                  onClick={() => handlePick(s.subject_id)}
                  disabled={loggingIn !== null}
                />
              ))}
            </div>
          </section>
        )}

        {/* Liver cohort */}
        {liverSubjects.length > 0 && (
          <section className="mt-8">
            <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold text-orange-700">
              <span className="inline-block h-3 w-3 rounded-full bg-orange-400" />
              脂肪肝受试者
              <span className="text-xs font-normal text-slate-500">({liverSubjects.length} 人)</span>
            </h2>
            <div className="grid grid-cols-4 gap-3 sm:grid-cols-6 md:grid-cols-8 lg:grid-cols-10">
              {liverSubjects.map((s) => (
                <SubjectCard
                  key={s.subject_id}
                  subject={s}
                  onClick={() => handlePick(s.subject_id)}
                  disabled={loggingIn !== null}
                />
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  )
}

/* ── Root ───────────────────────────────────────────────────── */

export default function App() {
  const [authed, setAuthed] = useState(Boolean(getToken()))

  return (
    <QueryClientProvider client={queryClient}>
      {!authed ? (
        <AuthPanel onAuthed={() => setAuthed(true)} />
      ) : (
        <BrowserRouter>
          <AppRoutes
            onLogout={() => {
              clearToken()
              localStorage.removeItem('metabodash_subject')
              setAuthed(false)
            }}
          />
        </BrowserRouter>
      )}
    </QueryClientProvider>
  )
}
