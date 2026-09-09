import { useEffect, useState, type ReactNode } from 'react'
import { studyPlansApi } from '../../api/studyPlans'
import { AppLink, navigate } from '../../app/router'

const navItems = [
  { to: '/dashboard', label: '工作台' },
  { to: '/jobs', label: '岗位' },
  { to: '/resumes', label: '简历' },
  { to: '/match-reports', label: '匹配报告' },
]

function routeNumber(pathname: string, pattern: RegExp): number | null {
  const match = pathname.match(pattern)
  return match ? Number(match[1]) : null
}

function StudyPlanNavigation({ pathname }: { pathname: string }) {
  const planId = routeNumber(pathname, /^\/study-plans\/(\d+)$/)
  const reportPageId = routeNumber(pathname, /^\/match-reports\/(\d+)$/)
  const [context, setContext] = useState<{
    pathname: string
    reportId: number | null
    planId: number | null
  } | null>(null)
  const [expanded, setExpanded] = useState(Boolean(planId))

  useEffect(() => {
    let current = true
    if (!planId && !reportPageId) {
      return () => { current = false }
    }
    const request = planId
      ? studyPlansApi.get(planId).then((plan) => ({ reportId: plan.match_report_id, planId: plan.id }))
      : studyPlansApi.list({ matchReportId: reportPageId! }).then((plans) => ({
        reportId: reportPageId,
        planId: plans[0]?.id ?? null,
      }))
    request.then((context) => {
      if (!current) return
      setContext({ pathname, ...context })
      if (planId) setExpanded(true)
    }).catch(() => {
      if (current) setContext({ pathname, reportId: reportPageId, planId: null })
    })
    return () => { current = false }
  }, [pathname, planId, reportPageId])

  const resolvedContext = context?.pathname === pathname ? context : null
  const reportId = resolvedContext?.reportId ?? reportPageId
  const currentPlanId = resolvedContext?.planId ?? null
  const loading = Boolean((planId || reportPageId) && !resolvedContext)
  const inPlanSection = pathname === '/study-plans' || Boolean(planId)
  function handleToggle() {
    if (reportId === null) {
      navigate('/study-plans')
      return
    }
    setExpanded((value) => !value)
  }

  return (
    <div className="nav-group">
      <button
        type="button"
        className={inPlanSection ? 'nav-item nav-toggle active' : 'nav-item nav-toggle'}
        aria-expanded={expanded}
        onClick={handleToggle}
      >
        <span>学习计划</span><span aria-hidden="true">{expanded ? '▾' : '▸'}</span>
      </button>
      {expanded && reportId !== null && (
        <div className="nav-submenu">
          {loading ? <span className="nav-empty">正在读取计划…</span> : currentPlanId ? (
            <>
              <AppLink
                to={`/study-plans/${currentPlanId}`}
                className={planId === currentPlanId ? 'nav-subitem active' : 'nav-subitem'}
              >当前计划</AppLink>
              <span className="nav-context">匹配报告 #{reportId}</span>
            </>
          ) : <span className="nav-empty">暂无计划，请先从报告生成</span>}
        </div>
      )}
    </div>
  )
}

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
          <StudyPlanNavigation pathname={pathname} />
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
              <AppLink to="/study-plans" className="nav-item">学习计划</AppLink>
            </nav>
          </details>
        </header>
        <main className="page-container">{children}</main>
      </div>
    </div>
  )
}
