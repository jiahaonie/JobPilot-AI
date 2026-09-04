import { routeId, usePathname } from './app/router'
import { AppShell } from './components/layout/AppShell'
import { DashboardPage } from './pages/DashboardPage'
import { JobDetailPage } from './pages/JobDetailPage'
import { JobsPage, NewJobPage } from './pages/JobsPage'
import { MatchReportDetailPage, MatchReportsPage } from './pages/MatchReportsPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { ResumeDetailPage } from './pages/ResumeDetailPage'
import { ResumesPage } from './pages/ResumesPage'
import { StudyPlanDetailPage, StudyPlansPage } from './pages/StudyPlansPage'

function CurrentPage({ pathname }: { pathname: string }) {
  if (pathname === '/') {
    return <DashboardPage />
  }
  if (pathname === '/dashboard') return <DashboardPage />
  if (pathname === '/jobs') return <JobsPage />
  if (pathname === '/jobs/new') return <NewJobPage />
  if (/^\/jobs\/\d+$/.test(pathname)) return <JobDetailPage jobId={routeId(pathname)!} />
  if (pathname === '/resumes') return <ResumesPage />
  if (/^\/resumes\/\d+$/.test(pathname)) return <ResumeDetailPage resumeId={routeId(pathname)!} />
  if (pathname === '/match-reports') return <MatchReportsPage />
  if (/^\/match-reports\/\d+$/.test(pathname)) return <MatchReportDetailPage reportId={routeId(pathname)!} />
  if (pathname === '/study-plans') return <StudyPlansPage />
  if (/^\/study-plans\/\d+$/.test(pathname)) return <StudyPlanDetailPage planId={routeId(pathname)!} />
  return <NotFoundPage />
}

export default function AppRoot() {
  const pathname = usePathname()
  return <AppShell pathname={pathname}><CurrentPage pathname={pathname} /></AppShell>
}
