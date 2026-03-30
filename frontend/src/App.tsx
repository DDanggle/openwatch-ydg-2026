import { Routes, Route } from 'react-router-dom'
import AppShell from './components/layout/AppShell'
import LeaderboardPage from './components/leaderboard/LeaderboardPage'
import DetailPage from './components/detail/DetailPage'
import DebatePanel from './components/debate/DebatePanel'
import GapPage from './components/gap/GapPage'

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<GapPage />} />
        <Route path="/ranking" element={<LeaderboardPage />} />
        <Route path="/politician/:id" element={<DetailPage />} />
        <Route path="/politician/:id/debate" element={<DebatePanel />} />
      </Route>
    </Routes>
  )
}
