import { Link, Outlet, useLocation } from 'react-router-dom'

const NAV = [
  { path: '/', label: '부동산 괴리' },
  { path: '/ranking', label: '의원 랭킹' },
]

export default function AppShell() {
  const { pathname } = useLocation()

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/" className="text-xl font-bold text-slate-800 hover:text-slate-600">
            누가 진짜 부자가 되었나?
          </Link>
          <nav className="flex items-center gap-1">
            {NAV.map((n) => (
              <Link
                key={n.path}
                to={n.path}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  pathname === n.path
                    ? 'bg-slate-800 text-white'
                    : 'text-slate-500 hover:bg-slate-100'
                }`}
              >
                {n.label}
              </Link>
            ))}
            <span className="text-xs text-slate-300 ml-3">POC v0.3</span>
          </nav>
        </div>
      </header>
      <main className="max-w-7xl mx-auto px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
