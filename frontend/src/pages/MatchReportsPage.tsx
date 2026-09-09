import { useCallback, useState } from 'react'
import { ApiError } from '../api/client'
import { matchReportsApi } from '../api/matchReports'
import { studyPlansApi } from '../api/studyPlans'
import { AppLink, navigate } from '../app/router'
import { EmptyState, ErrorState, InlineMessage, LoadingState } from '../components/feedback/PageState'
import { SkillTags } from '../components/ui/StatusBadge'
import { useAsyncResource } from '../hooks/useAsyncResource'
import { formatDate, scoreText } from '../utils/format'
import type { RequirementMatch } from '../types/api'

const requirementStatusLabel = {
  covered: '已覆盖',
  partial: '部分覆盖',
  missing: '尚未覆盖',
} as const

function RequirementMatches({ matches }: { matches: RequirementMatch[] }) {
  return (
    <section className="panel">
      <div className="section-heading"><div><p className="eyebrow">V2 要求级解释</p><h2>岗位技能组覆盖情况</h2></div></div>
      <div className="requirement-list">
        {matches.map((match, matchIndex) => (
          <article className={`requirement-card ${match.status}`} key={`${match.label}-${matchIndex}`}>
            <div className="requirement-heading">
              <div><strong>{match.label}</strong><p>{match.importance === 'required' ? '必需能力' : '加分能力'} · {match.match_mode === 'any' ? '任意一项满足即可' : '需要全部满足'}</p></div>
              <span className={`status-badge ${match.status}`}>{requirementStatusLabel[match.status]}</span>
            </div>
            <p className="evidence"><strong>JD 证据：</strong>{match.job_evidence}</p>
            <div className="option-list">
              {match.options.map((option, optionIndex) => (
                <div key={`${option.option}-${optionIndex}`}>
                  <strong>{option.option}</strong>
                  {option.matched_resume_skill ? <span className="matched-option">命中：{option.matched_resume_skill}</span> : <span className="missing-option">未命中</span>}
                  {option.resume_evidence && <p>简历证据：{option.resume_evidence}</p>}
                </div>
              ))}
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}

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
  const planLoader = useCallback(() => studyPlansApi.list({ matchReportId: reportId }), [reportId])
  const planResource = useAsyncResource(planLoader)
  const [deadline, setDeadline] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function createPlan() {
    setBusy(true); setError(null)
    try {
      const existing = planResource.data?.[0]
      if (existing) return navigate(`/study-plans/${existing.id}`)
      const plan = await studyPlansApi.create(reportId, deadline || null)
      navigate(`/study-plans/${plan.id}`)
    } catch (reason) {
      if (
        reason instanceof ApiError &&
        (reason.code === 'PLAN_GENERATION_TIMEOUT' || reason.status === null)
      ) {
        try {
          const existing = (await studyPlansApi.list({ matchReportId: reportId }))[0]
          if (existing) return navigate(`/study-plans/${existing.id}`)
          setError('暂未确认生成结果，请重试查看。')
          return
        } catch { /* 保留未知状态。 */ }
      }
      if (reason instanceof ApiError) {
        const messages: Record<string, string> = {
          NO_PRIORITY_SKILLS: '当前报告没有需要优先补齐的技能，无须生成计划。',
          INSUFFICIENT_KNOWLEDGE: '当前内置资料不足以支持这些技能，暂未生成计划。',
          KNOWLEDGE_UNAVAILABLE: '内置资料暂时不可用，请稍后重试。',
          PLAN_GENERATION_FAILED: '生成失败，计划尚未保存。请重试。',
          PLAN_PERSISTENCE_FAILED: '保存失败，计划尚未保存。请重试。',
        }
        setError(reason.code ? messages[reason.code] ?? reason.message : reason.message)
      } else setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setBusy(false)
    }
  }

  if (resource.loading) return <LoadingState />
  if (resource.error) return <ErrorState error={resource.error} onRetry={resource.reload} />
  const report = resource.data!
  const existingPlan = planResource.data?.[0]
  return (
    <>
      <div className="page-heading"><div><p className="eyebrow">报告 #{report.id} · {report.scoring_version}</p><h1>技能匹配解释</h1><p>生成于 {formatDate(report.created_at)}</p></div><div className="score-hero"><strong>{scoreText(report.skill_coverage_score)}</strong><span>技能覆盖分</span></div></div>
      <InlineMessage kind="info">{report.score_disclaimer}</InlineMessage>
      {!report.requirement_matches && <InlineMessage kind="info">这是旧版匹配算法生成的历史报告，仅保留原始结果，不提供 V2 要求级解释。</InlineMessage>}
      <section className="score-grid"><article><span>必需技能</span><strong>{scoreText(report.required_score)}</strong></article><article><span>加分技能</span><strong>{scoreText(report.preferred_score)}</strong></article><article><span>岗位 / 简历</span><strong>#{report.job_id} / #{report.resume_id}</strong></article></section>
      {report.requirement_matches && <RequirementMatches matches={report.requirement_matches} />}
      <div className="two-column">
        <section className="panel"><p className="eyebrow">已经覆盖</p><h2>匹配与加分技能</h2><h3>匹配技能</h3><SkillTags skills={report.matched_skills} /><h3>额外覆盖</h3><SkillTags skills={report.bonus_skills} /></section>
        <section className="panel"><p className="eyebrow">需要补齐</p><h2>优先学习技能</h2>{report.priority_skills.length ? <div className="gap-list">{report.priority_skills.map((gap) => <article key={gap.skill}><strong>{gap.skill}</strong><p>{gap.evidence || '没有对应的 JD 原文证据'}</p></article>)}</div> : <p className="muted">没有优先技能缺口。</p>}</section>
      </div>
      <section className="panel"><div className="section-heading"><div><p className="eyebrow">全部差距</p><h2>缺失技能与 JD 证据</h2></div></div>{report.missing_skills.length ? <div className="gap-list">{report.missing_skills.map((gap) => <article key={gap.skill}><strong>{gap.skill}</strong><p>{gap.evidence || '没有对应的 JD 原文证据'}</p></article>)}</div> : <p className="muted">没有缺失的必需技能。</p>}</section>
      <section className="panel plan-creator"><div><p className="eyebrow">把技能差距，变成下一步行动</p><h2>结合内置资料生成学习计划</h2><p className="muted">每项任务包含具体行动、完成标准和参考原文；生成成功后自动保存，一份匹配报告对应一份计划。</p></div>{!existingPlan && <label><span>截止日期（可选）</span><input type="date" min={new Date().toISOString().slice(0, 10)} value={deadline} onChange={(event) => setDeadline(event.target.value)} /></label>}<button className="button primary" disabled={busy || planResource.loading || !report.priority_skills.length} onClick={createPlan}>{busy ? '正在生成学习计划…' : existingPlan ? '查看学习计划' : '生成学习计划'}</button></section>
      {error && <InlineMessage kind="error">{error}</InlineMessage>}
    </>
  )
}
