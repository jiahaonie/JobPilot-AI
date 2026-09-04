import { useCallback, useState } from 'react'
import { ApiError } from '../api/client'
import { matchReportsApi } from '../api/matchReports'
import { studyPlansApi } from '../api/studyPlans'
import { AppLink, navigate } from '../app/router'
import { EmptyState, ErrorState, InlineMessage, LoadingState } from '../components/feedback/PageState'
import { SkillTags } from '../components/ui/StatusBadge'
import { useAsyncResource } from '../hooks/useAsyncResource'
import { formatDate, scoreText } from '../utils/format'

export function MatchReportsPage() {
  const loader = useCallback(() => matchReportsApi.list(), [])
  const resource = useAsyncResource(loader)
  return (
    <>
      <div className="page-heading"><div><p className="eyebrow">可解释快照</p><h1>匹配报告</h1><p>每份报告都保留生成时的岗位要求和简历技能。</p></div></div>
      {resource.loading ? <LoadingState /> : resource.error ? <ErrorState error={resource.error} onRetry={resource.reload} /> : !resource.data?.length ? (
        <EmptyState title="还没有匹配报告" description="在岗位详情完成两侧分析后生成第一份报告。" action={<AppLink to="/jobs" className="button primary">前往岗位</AppLink>} />
      ) : <div className="card-grid">{resource.data.slice().reverse().map((report) => (
        <article className="entity-card report-card" key={report.id}><div className="card-topline"><span>报告 #{report.id}</span><span className="score-small">{scoreText(report.skill_coverage_score)}</span></div><h2>岗位 #{report.job_id} × 简历 #{report.resume_id}</h2><SkillTags skills={report.priority_skills.map((item) => item.skill)} empty="没有优先技能缺口" /><small className="muted">{formatDate(report.created_at)} · {report.scoring_version}</small><div className="card-actions"><AppLink className="button secondary" to={`/match-reports/${report.id}`}>查看解释</AppLink></div></article>
      ))}</div>}
    </>
  )
}

export function MatchReportDetailPage({ reportId }: { reportId: number }) {
  const loader = useCallback(() => matchReportsApi.get(reportId), [reportId])
  const resource = useAsyncResource(loader)
  const [deadline, setDeadline] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function createPlan() {
    setBusy(true); setError(null)
    try {
      const plan = await studyPlansApi.create(reportId, deadline || null)
      navigate(`/study-plans/${plan.id}`)
    } catch (reason) {
      if (reason instanceof ApiError && reason.status === 409) {
        try {
          const existing = (await studyPlansApi.list()).find((plan) => plan.match_report_id === reportId)
          if (existing) return navigate(`/study-plans/${existing.id}`)
        } catch { /* 保留原始冲突信息。 */ }
      }
      setError(reason instanceof Error ? reason.message : String(reason))
      setBusy(false)
    }
  }

  if (resource.loading) return <LoadingState />
  if (resource.error) return <ErrorState error={resource.error} onRetry={resource.reload} />
  const report = resource.data!
  return (
    <>
      <div className="page-heading"><div><p className="eyebrow">报告 #{report.id} · {report.scoring_version}</p><h1>技能匹配解释</h1><p>生成于 {formatDate(report.created_at)}</p></div><div className="score-hero"><strong>{scoreText(report.skill_coverage_score)}</strong><span>技能覆盖分</span></div></div>
      {error && <InlineMessage kind="error">{error}</InlineMessage>}
      <InlineMessage kind="info">{report.score_disclaimer}</InlineMessage>
      <section className="score-grid"><article><span>必需技能</span><strong>{scoreText(report.required_score)}</strong></article><article><span>加分技能</span><strong>{scoreText(report.preferred_score)}</strong></article><article><span>岗位 / 简历</span><strong>#{report.job_id} / #{report.resume_id}</strong></article></section>
      <div className="two-column">
        <section className="panel"><p className="eyebrow">已经覆盖</p><h2>匹配与加分技能</h2><h3>匹配技能</h3><SkillTags skills={report.matched_skills} /><h3>额外覆盖</h3><SkillTags skills={report.bonus_skills} /></section>
        <section className="panel"><p className="eyebrow">需要补齐</p><h2>优先学习技能</h2>{report.priority_skills.length ? <div className="gap-list">{report.priority_skills.map((gap) => <article key={gap.skill}><strong>{gap.skill}</strong><p>{gap.evidence || '没有对应的 JD 原文证据'}</p></article>)}</div> : <p className="muted">没有优先技能缺口。</p>}</section>
      </div>
      <section className="panel"><div className="section-heading"><div><p className="eyebrow">全部差距</p><h2>缺失技能与 JD 证据</h2></div></div>{report.missing_skills.length ? <div className="gap-list">{report.missing_skills.map((gap) => <article key={gap.skill}><strong>{gap.skill}</strong><p>{gap.evidence || '没有对应的 JD 原文证据'}</p></article>)}</div> : <p className="muted">没有缺失的必需技能。</p>}</section>
      <section className="panel plan-creator"><div><p className="eyebrow">转为行动</p><h2>基于此快照创建学习计划</h2><p className="muted">同一报告只能创建一份计划；发生冲突时会打开已有计划。</p></div><label><span>截止日期（可选）</span><input type="date" min={new Date().toISOString().slice(0, 10)} value={deadline} onChange={(event) => setDeadline(event.target.value)} /></label><button className="button primary" disabled={busy || !report.priority_skills.length} onClick={createPlan}>{busy ? '正在创建…' : '创建学习计划'}</button></section>
    </>
  )
}
