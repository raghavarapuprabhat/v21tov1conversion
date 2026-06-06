import { Routes, Route, NavLink } from 'react-router-dom'
import LandingPage from './pages/LandingPage'
import GapTablePage from './pages/GapTablePage'
import TreePage from './pages/TreePage'
import { useHealth } from './api/queries'
import { DisplayNameProvider, useDisplayName } from './state/displayName'
import DisplayNamePrompt from './components/DisplayNamePrompt'

function ApiStatus() {
  const health = useHealth()
  const base =
    'inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium ring-1'
  if (health.isLoading)
    return (
      <span className={`${base} bg-amber-50 text-amber-700 ring-amber-200`}>
        <span className="h-2 w-2 rounded-full bg-amber-400 animate-pulse" /> Connecting…
      </span>
    )
  if (health.isError)
    return (
      <span className={`${base} bg-rose-50 text-rose-700 ring-rose-200`} title="Backend unreachable">
        <span className="h-2 w-2 rounded-full bg-rose-500" /> API offline
      </span>
    )
  return (
    <span className={`${base} bg-emerald-50 text-emerald-700 ring-emerald-200`} title={`v${health.data?.version}`}>
      <span className="h-2 w-2 rounded-full bg-emerald-500" /> API · {health.data?.storage}
    </span>
  )
}

function NavItem({ to, children, end }: { to: string; children: React.ReactNode; end?: boolean }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
          isActive
            ? 'bg-brand-50 text-brand-700'
            : 'text-slate-500 hover:bg-slate-100 hover:text-slate-900'
        }`
      }
    >
      {children}
    </NavLink>
  )
}

function Identity() {
  const { name, setName } = useDisplayName()
  if (!name) return null
  return (
    <button
      onClick={() => setName('')}
      title="Change display name"
      className="flex items-center gap-2 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600 hover:bg-slate-200"
    >
      <span className="grid h-5 w-5 place-items-center rounded-full bg-brand-600 text-[10px] text-white">
        {name.slice(0, 1).toUpperCase()}
      </span>
      {name}
    </button>
  )
}

function Shell() {
  return (
    <div className="min-h-full">
      <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center gap-4 px-6 py-3">
          <div className="flex items-center gap-2">
            <div className="grid h-8 w-8 place-items-center rounded-lg bg-brand-600 text-sm font-bold text-white">
              GA
            </div>
            <div className="leading-tight">
              <div className="text-sm font-semibold text-slate-900">V2.1 → V1 Gap Analysis</div>
              <div className="text-[11px] text-slate-400">Schema conversion impact</div>
            </div>
          </div>
          <nav className="ml-4 flex items-center gap-1">
            <NavItem to="/" end>
              Gaps
            </NavItem>
            <NavItem to="/tree">V1 Tree</NavItem>
          </nav>
          <div className="ml-auto flex items-center gap-3">
            <Identity />
            <ApiStatus />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/gaps/:type" element={<GapTablePage />} />
          <Route path="/tree" element={<TreePage />} />
        </Routes>
      </main>

      <DisplayNamePrompt />
    </div>
  )
}

export default function App() {
  return (
    <DisplayNameProvider>
      <Shell />
    </DisplayNameProvider>
  )
}
