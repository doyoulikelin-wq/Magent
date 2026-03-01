import { NavLink } from 'react-router-dom'

type NavItem = { label: string; to: string; icon: string }

const primary: NavItem[] = [
  { label: '今日简报', to: '/app/today', icon: '📋' },
  { label: '吃前预演', to: '/app/premeal', icon: '🔮' },
  { label: '吃后补救', to: '/app/rescue', icon: '🚑' },
  { label: '周目标', to: '/app/weekly', icon: '🎯' },
  { label: '证据解释', to: '/app/evidence', icon: '🔍' },
]

const secondary: NavItem[] = [
  { label: '健康数据', to: '/app/health', icon: '📊' },
  { label: '饮食上传', to: '/app/meals', icon: '📷' },
  { label: 'Chatbot', to: '/app/chat', icon: '💬' },
]

function NavSection({ items }: { items: NavItem[] }) {
  return (
    <nav className="grid grid-cols-2 gap-1.5 md:grid-cols-1">
      {items.map((link) => (
        <NavLink
          key={link.to}
          to={link.to}
          className={({ isActive }) =>
            [
              'flex items-center gap-2 rounded-xl px-3 py-2 text-sm transition-colors',
              isActive
                ? 'bg-primary text-white shadow-soft'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200',
            ].join(' ')
          }
        >
          <span className="text-base">{link.icon}</span>
          {link.label}
        </NavLink>
      ))}
    </nav>
  )
}

export function Sidebar() {
  const subjectId = localStorage.getItem('metabodash_subject')

  return (
    <aside className="w-full border-b border-slate-200 bg-white/80 p-4 md:w-64 md:border-b-0 md:border-r">
      <div className="mb-1 font-heading text-xl font-bold text-slate-900">MetaboDash</div>
      {subjectId && (
        <div className="mb-3 inline-block rounded-full bg-teal-100 px-3 py-0.5 text-xs font-semibold text-teal-700">
          {subjectId}
        </div>
      )}
      <div className="mb-2 text-[10px] font-medium uppercase tracking-wider text-slate-400">
        代理服务
      </div>
      <NavSection items={primary} />
      <div className="mb-2 mt-4 text-[10px] font-medium uppercase tracking-wider text-slate-400">
        历史数据
      </div>
      <NavSection items={secondary} />
      <div className="mt-4">
        <NavLink
          to="/app/settings"
          className={({ isActive }) =>
            [
              'flex items-center gap-2 rounded-xl px-3 py-2 text-sm transition-colors',
              isActive
                ? 'bg-primary text-white shadow-soft'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200',
            ].join(' ')
          }
        >
          <span className="text-base">⚙️</span>
          设置
        </NavLink>
      </div>
    </aside>
  )
}
