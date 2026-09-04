import type { ReactNode } from 'react'
import { AppLink } from '../../app/router'

const navItems = [
  { to: '/dashboard', label: '工作台' },
  { to: '/jobs', label: '岗位' },
  { to: '/resumes', label: '简历' },
  { to: '/match-reports', label: '匹配报告' },
  { to: '/study-plans', label: '学习计划' },
]

export function AppShell({ pathname, children }: { pathname: string; children: ReactNode }) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <AppLink to="/dashboard" className="brand">
          <span className="brand-mark">JP</span>
          <span>
            <strong>JobPilot AI</strong>
            <small>求职准备工作台</small>
          </span>
        </AppLink>
        <nav aria-label="主导航">
          {navItems.map((item) => {
            const active =
              pathname === item.to ||
              (item.to !== '/dashboard' && pathname.startsWith(`${item.to}/`))
            return (
              <AppLink key={item.to} to={item.to} className={active ? 'nav-item active' : 'nav-item'}>
                {item.label}
              </AppLink>
            )
          })}
        </nav>
        <div className="sidebar-note">本地单用户 MVP</div>
      </aside>
      <div className="main-column">
        <header className="mobile-header">
          <AppLink to="/dashboard" className="brand compact">
            <span className="brand-mark">JP</span>
            <strong>JobPilot AI</strong>
          </AppLink>
          <details className="mobile-menu">
            <summary>导航</summary>
            <nav>
              {navItems.map((item) => (
                <AppLink key={item.to} to={item.to} className="nav-item">
                  {item.label}
                </AppLink>
              ))}
            </nav>
          </details>
        </header>
        <main className="page-container">{children}</main>
      </div>
    </div>
  )
}
