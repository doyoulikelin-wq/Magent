type Props = {
  title: string
  subtitle?: string
  onLogout: () => void
}

export function TopBar({ title, subtitle, onLogout }: Props) {
  return (
    <header className="sticky top-0 z-10 flex items-center justify-between border-b border-slate-200 bg-white/80 px-5 py-4 backdrop-blur">
      <div>
        <div className="text-xs uppercase tracking-wide text-slate-500">MetaboDash MVP</div>
        <h1 className="font-heading text-2xl font-semibold text-slate-900">{title}</h1>
        {subtitle ? <p className="text-sm text-slate-500">{subtitle}</p> : null}
      </div>
      <button
        onClick={onLogout}
        className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700 transition hover:bg-slate-100"
      >
        退出登录
      </button>
    </header>
  )
}
