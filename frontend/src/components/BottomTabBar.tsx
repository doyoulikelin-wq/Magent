import { NavLink } from 'react-router-dom'

const tabs = [
  { to: '/', icon: '🏠', label: '首页' },
  { to: '/health', icon: '📊', label: '健康数据' },
  { to: '/glucose', icon: '📈', label: '动态数据' },
  { to: '/food', icon: '🍽️', label: '吃了什么' },
]

export function BottomTabBar() {
  return (
    <nav className="fixed inset-x-0 bottom-0 z-50 border-t border-slate-200 bg-white/90 pb-[env(safe-area-inset-bottom)] backdrop-blur-md">
      <div className="mx-auto flex max-w-lg">
        {tabs.map((t) => (
          <NavLink
            key={t.to}
            to={t.to}
            end={t.to === '/'}
            className={({ isActive }) =>
              [
                'flex flex-1 flex-col items-center gap-0.5 py-2 text-[10px] font-medium transition-colors',
                isActive ? 'text-teal-700' : 'text-slate-400 hover:text-slate-600',
              ].join(' ')
            }
          >
            <span className="text-xl leading-none">{t.icon}</span>
            {t.label}
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
