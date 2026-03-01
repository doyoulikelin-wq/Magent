import { ReactNode } from 'react'

import { Sidebar } from './Sidebar'
import { TopBar } from './TopBar'

type Props = {
  title: string
  subtitle?: string
  onLogout: () => void
  children: ReactNode
}

export function PageShell({ title, subtitle, onLogout, children }: Props) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-teal-50 via-cyan-50 to-orange-50 md:flex">
      <Sidebar />
      <main className="min-w-0 flex-1">
        <TopBar title={title} subtitle={subtitle} onLogout={onLogout} />
        <section className="animate-fadeUp p-5">{children}</section>
      </main>
    </div>
  )
}
