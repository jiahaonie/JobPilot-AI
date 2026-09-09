import { useCallback, useState } from 'react'
import { studyPlansApi } from '../api/studyPlans'
import { AppLink } from '../app/router'
import { EmptyState, ErrorState, InlineMessage, LoadingState } from '../components/feedback/PageState'
import { StatusBadge } from '../components/ui/StatusBadge'
import { useAsyncResource } from '../hooks/useAsyncResource'
import { taskPhaseLabels, taskStatusLabels, type StudyTaskStatus } from '../types/api'
import { formatDate } from '../utils/format'

const allowedTaskStatuses: Record<StudyTaskStatus, StudyTaskStatus[]> = {
  todo: ['todo', 'in_progress', 'done'],
  in_progress: ['todo', 'in_progress', 'done'],
  done: ['in_progress', 'done'],
}

const coverageReasonLabels: Record<string, string> = {
  no_relevant_evidence: '未找到足够相关的参考资料',
  insufficient_support: '现有片段不足以支持具体任务',
}

export function StudyPlansPage() {
  const loader = useCallback(() => studyPlansApi.list(), [])
  const resource = useAsyncResource(loader)
  return (
    <>
      <div className="page-heading"><div><p className="eyebrow">从差距到行动</p><h1>学习计划</h1><p>计划进度由每项任务的真实状态动态汇总。</p></div></div>
      {resource.loading ? <LoadingState /> : resource.error ? <ErrorState error={resource.error} onRetry={resource.reload} /> : !resource.data?.length ? (
        <EmptyState title="还没有学习计划" description="先生成匹配报告，再把优先技能差距转成任务。" action={<AppLink to="/match-reports" className="button primary">查看匹配报告</AppLink>} />
      ) : <div className="card-grid">{resource.data.slice().reverse().map((plan) => {
        const percent = plan.task_count ? Math.round(plan.completed_count / plan.task_count * 100) : 0
        const missing = plan.coverage?.uncovered_skills ?? []
        return <article className="entity-card" key={plan.id}><div className="card-topline"><span>计划 #{plan.id}</span><StatusBadge status={plan.status} /></div><h2>报告 #{plan.match_report_id} 的学习计划</h2><div className="progress-track"><span style={{ width: `${percent}%` }} /></div><p>{plan.completed_count} / {plan.task_count} 项完成 · {percent}%</p>{missing.length > 0 && <p className="coverage-summary">部分覆盖：{missing.map((item) => item.skill).join('、')} 暂缺资料</p>}<small className="muted">截止：{plan.deadline ? formatDate(plan.deadline, true) : '未设置 · 自主安排'}</small><div className="card-actions"><AppLink className="button secondary" to={`/study-plans/${plan.id}`}>继续学习</AppLink></div></article>
      })}</div>}
    </>
  )
}

export function StudyPlanDetailPage({ planId }: { planId: number }) {
  const loader = useCallback(() => studyPlansApi.get(planId), [planId])
  const resource = useAsyncResource(loader)
  const [busyTask, setBusyTask] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function updateTask(taskId: number, status: StudyTaskStatus) {
    setBusyTask(taskId); setError(null)
    try { await studyPlansApi.updateTask(taskId, status); resource.reload() }
    catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)) }
    finally { setBusyTask(null) }
  }

  if (resource.loading) return <LoadingState />
  if (resource.error) return <ErrorState error={resource.error} onRetry={resource.reload} />
  const plan = resource.data!
  const percent = plan.task_count ? Math.round(plan.completed_count / plan.task_count * 100) : 0
  const skills = Array.from(new Set(plan.tasks.map((task) => task.skill)))
  const coverage = plan.coverage
  return (
    <>
      <div className="page-heading"><div><p className="eyebrow">计划 #{plan.id} · 报告 #{plan.match_report_id}</p><h1>技能补齐计划</h1><p>截止：{plan.deadline ? formatDate(plan.deadline, true) : '未设置 · 自主安排'}</p><AppLink to={`/match-reports/${plan.match_report_id}`}>查看匹配报告</AppLink></div><StatusBadge status={plan.status} /></div>
      {error && <InlineMessage kind="error">{error}</InlineMessage>}
      {plan.generation_method === 'rule_v1' && <InlineMessage kind="info">此计划由早期规则生成，未附参考原文。</InlineMessage>}
      <section className="panel progress-panel"><div><strong>{percent}%</strong><span>{plan.completed_count} / {plan.task_count} 项任务完成</span></div><div><div className="progress-track large"><span style={{ width: `${percent}%` }} /></div>{percent === 100 && <p className="completion-note">本计划任务已完成。你仍可以保留内容和依据用于回顾。</p>}</div></section>
      {coverage && <section className="panel coverage-panel"><div><p className="eyebrow">技能覆盖范围</p><h2>已覆盖 {coverage.covered_skills.length} / {coverage.target_skills.length} 项优先技能</h2><p>已覆盖：{coverage.covered_skills.join('、')}</p></div>{coverage.uncovered_skills.length > 0 ? <div className="coverage-warning"><strong>本次未生成任务</strong>{coverage.uncovered_skills.map((item) => <p key={item.skill}>{item.skill}：{coverageReasonLabels[item.reason_code] ?? '资料不足'}</p>)}</div> : <InlineMessage kind="success">已覆盖当前报告的全部优先技能。</InlineMessage>}</section>}
      <div className="skill-sections">{skills.map((skill) => <section className="panel" key={skill}><div className="section-heading"><div><p className="eyebrow">目标技能</p><h2>{skill}</h2></div></div><div className="task-list">{plan.tasks.filter((task) => task.skill === skill).map((task) => <article className={task.status === 'done' ? 'task-card completed' : 'task-card'} key={task.id}><div className="task-order">{task.position}</div><div className="task-content"><div className="card-topline"><span className="phase-label">{taskPhaseLabels[task.phase]}</span><StatusBadge status={task.status} /></div><h3>{task.title}</h3>{task.learning_content && <div className="task-field"><strong>学习内容</strong><p>{task.learning_content}</p></div>}{task.action && <div className="task-field"><strong>具体行动</strong><p>{task.action}</p></div>}<div className="task-field"><strong>完成标准</strong><p>{task.completion_criteria}</p></div>{task.evidence?.length ? <details className="evidence-details"><summary>参考依据 · {task.evidence[0].source_name}</summary>{task.evidence.map((item) => <blockquote key={item.chunk_id}><strong>{item.source_name}</strong>{item.location && <small>{item.location}</small>}<p>{item.excerpt}</p></blockquote>)}</details> : task.resource_query ? <small>资源搜索词：{task.resource_query}</small> : null}{task.due_date && <small>截止：{formatDate(task.due_date, true)}</small>}</div><label className="task-control"><span>任务状态</span><select disabled={busyTask === task.id} value={task.status} onChange={(event) => updateTask(task.id, event.target.value as StudyTaskStatus)}>{allowedTaskStatuses[task.status].map((status) => <option value={status} key={status}>{taskStatusLabels[status]}</option>)}</select></label></article>)}</div></section>)}</div>
    </>
  )
}
