import { GraduationCap, Upload, Users } from 'lucide-react'
import { Link, NavLink, Outlet } from 'react-router-dom'
import { cn } from '@/lib/utils'

const navItems = [
  { to: '/import', label: 'Import', icon: Upload },
  { to: '/students', label: 'Students', icon: Users },
]

export default function Layout() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="print-hidden sticky top-0 z-20 border-b bg-card/85 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center gap-6 px-4 sm:px-6">
          <Link to="/students" className="flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-violet-500 text-white shadow-sm">
              <GraduationCap className="h-5 w-5" />
            </span>
            <span className="leading-tight">
              <span className="block text-sm font-semibold tracking-tight">Result Portal</span>
              <span className="block text-[11px] text-muted-foreground">Student results admin</span>
            </span>
          </Link>

          <nav className="ml-auto flex items-center gap-1" aria-label="Main">
            {navItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  cn(
                    'inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-accent text-accent-foreground'
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground',
                  )
                }
              >
                <Icon className="h-4 w-4" />
                {label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">
        <Outlet />
      </main>

      <footer className="print-hidden border-t py-5">
        <div className="mx-auto flex max-w-6xl flex-col gap-1 px-4 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <p>Result Portal · CSV import, student directory and report cards.</p>
          <p>Grading: A ≥ 80% · B ≥ 60% · C ≥ 50% · D ≥ 40% · F below 40%</p>
        </div>
      </footer>
    </div>
  )
}
