import { Navigate, Route, Routes } from 'react-router-dom'

import { BottomTabBar } from './components/BottomTabBar'
import { FoodPage } from './pages/FoodPage'
import { GlucosePage } from './pages/GlucosePage'
import { HealthDataPage } from './pages/HealthDataPage'
import { HomePage } from './pages/HomePage'
import { NewChatPage } from './pages/NewChatPage'

type Props = {
  onLogout: () => void
}

export function AppRoutes({ onLogout }: Props) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-teal-50 via-cyan-50 to-orange-50">
      <Routes>
        <Route path="/" element={<HomePage onLogout={onLogout} />} />
        <Route path="/health" element={<HealthDataPage />} />
        <Route path="/glucose" element={<GlucosePage />} />
        <Route path="/food" element={<FoodPage />} />
        <Route path="/chat" element={<NewChatPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <BottomTabBar />
    </div>
  )
}
