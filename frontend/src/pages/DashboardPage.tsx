import { useCallback } from 'react'
import { jobsApi } from '../api/jobs'
import { matchReportsApi } from '../api/matchReports'
import { resumesApi } from '../api/resumes'
import { studyPlansApi } from '../api/studyPlans'
import { AppLink } from '../app/router'
import { EmptyState, ErrorState, LoadingState } from '../components/feedback/PageState'
import { StatusBadge } from '../components/ui/StatusBadge'
import { useAsyncResource } from '../hooks/useAsyncResource'
import { formatDate, scoreText } from '../utils/format'

export function DashboardPage() {
  const loader = useCallback(async () => {
    const [jobs, resumes, reports, plans] = await Promise.all([
      jobsApi.list(), resumesApi.list(), matchReportsApi.list(), studyPlansApi.list(),
    ])
    return { jobs, resumes, reports, plans }
  }, [])
  const resource = useAsyncResource(loader)

  if (resource.loading) return <LoadingState label="正在汇总工作台…" />
  if (resource.error) return <ErrorState error={resource.error} onRetry={resource.reload} />
  const data = resource.data!
  const pendingJobs = data.jobs.filter((job) => job.analysis_status !== 'ready').length
  const pendingResumes = data.resumes.filter((resume) => resume.analysis_status !== 'ready').length
  const activePlans = data.plans.filter((plan) => plan.status !== 'completed')
  const recentReports = [...data.reports].sort((a, b) => b.id - a.id).slice(0, 3)

  return (
    <>
      <div className="page-heading hero-heading">
        <div>
          <p className="eyebrow">今天从最重要的一步开始</p>
          <h1>求职准备工作台</h1>
          <p>把岗位、简历、匹配差距和学习任务连接成一条可执行流程。</p>
        </div>
        <div className="heading-actions">
          <AppLink to="/jobs/new" className="button primary">创建岗位</AppLink>
          <AppLink to="/resumes" className="button secondary">上传简历</AppLink>
        </div>
      </div>

      <section className="stat-grid" aria-label="数据概览">
        <article className="stat-card"><span>岗位</span><strong>{data.jobs.length}</strong><small>{pendingJobs} 个待完成分析</small></article>
        <article className="stat-card"><span>简历</span><strong>{data.resumes.length}</strong><small>{pendingResumes} 份待完成分析</small></article>
        <article className="stat-card"><span>匹配报告</span><strong>{data.reports.length}</strong><small>不可变历史快照</small></article>
        <article className="stat-card"><span>学习计划</span><strong>{activePlans.length}</strong><small>进行中或未开始</small></article>
      </section>

      <div className="two-column">
        <section className="panel">
          <div className="section-heading"><div><p className="eyebrow">最近产出</p><h2>匹配报告</h2></div><AppLink to="/match-reports">查看全部</AppLink></div>
          {!recentReports.length ? (
            <EmptyState title="还没有匹配报告" description="先创建岗位并完成岗位与简历分析。" />
          ) : recentReports.map((report) => (
            <AppLink className="list-row" to={`/match-reports/${report.id}`} key={report.id}>
              <span><strong>报告 #{report.id}</strong><small>{formatDate(report.created_at)}</small></span>
              <span className="score-small">{scoreText(report.skill_coverage_score)}</span>
            </AppLink>
          ))}
        </section>
        <section className="panel">
          <div className="section-heading"><div><p className="eyebrow">下一步行动</p><h2>学习计划</h2></div><AppLink to="/study-plans">查看全部</AppLink></div>
          {!activePlans.length ? (
            <EmptyState title="暂无进行中的计划" description="从一份匹配报告创建学习计划。" />
          ) : activePlans.slice(0, 3).map((plan) => (
            <AppLink className="list-row" to={`/study-plans/${plan.id}`} key={plan.id}>
              <span><strong>计划 #{plan.id}</strong><small>{plan.completed_count}/{plan.task_count} 项完成</small></span>
              <StatusBadge status={plan.status} />
            </AppLink>
          ))}
        </section>
      </div>
    </>
  )
}
