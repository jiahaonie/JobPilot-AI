import { useCallback, useState } from 'react'
import { studyPlansApi } from '../api/studyPlans'
import { AppLink } from '../app/router'
import { EmptyState, ErrorState, InlineMessage, LoadingState } from '../components/feedback/PageState'
import { StatusBadge } from '../components/ui/StatusBadge'
import { useAsyncResource } from '../hooks/useAsyncResource'
import { taskPhaseLabels, taskStatusLabels, type StudyTaskStatus } from '../types/api'
import { formatDate } from '../utils/format'

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
        return <article className="entity-card" key={plan.id}><div className="card-topline"><span>计划 #{plan.id}</span><StatusBadge status={plan.status} /></div><h2>报告 #{plan.match_report_id} 的学习计划</h2><div className="progress-track"><span style={{ width: `${percent}%` }} /></div><p>{plan.completed_count} / {plan.task_count} 项完成 · {percent}%</p><small className="muted">截止：{plan.deadline ? formatDate(plan.deadline, true) : '未设置'}</small><div className="card-actions"><AppLink className="button secondary" to={`/study-plans/${plan.id}`}>继续学习</AppLink></div></article>
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
  return (
    <>
      <div className="page-heading"><div><p className="eyebrow">计划 #{plan.id} · 报告 #{plan.match_report_id}</p><h1>技能补齐计划</h1><p>截止：{plan.deadline ? formatDate(plan.deadline, true) : '未设置'}</p></div><StatusBadge status={plan.status} /></div>
      {error && <InlineMessage kind="error">{error}</InlineMessage>}
      <section className="panel progress-panel"><div><strong>{percent}%</strong><span>{plan.completed_count} / {plan.task_count} 项完成</span></div><div className="progress-track large"><span style={{ width: `${percent}%` }} /></div></section>
      <div className="skill-sections">{skills.map((skill) => <section className="panel" key={skill}><div className="section-heading"><div><p className="eyebrow">目标技能</p><h2>{skill}</h2></div></div><div className="task-list">{plan.tasks.filter((task) => task.skill === skill).map((task) => <article className={task.status === 'done' ? 'task-card completed' : 'task-card'} key={task.id}><div className="task-order">{task.position}</div><div className="task-content"><div className="card-topline"><span className="phase-label">{taskPhaseLabels[task.phase]}</span><StatusBadge status={task.status} /></div><h3>{task.title}</h3><p>{task.completion_criteria}</p><small>资源搜索词：{task.resource_query}</small>{task.due_date && <small>截止：{formatDate(task.due_date, true)}</small>}</div><label className="task-control"><span>任务状态</span><select disabled={busyTask === task.id} value={task.status} onChange={(event) => updateTask(task.id, event.target.value as StudyTaskStatus)}><option value="todo">{taskStatusLabels.todo}</option><option value="in_progress">{taskStatusLabels.in_progress}</option><option value="done">{taskStatusLabels.done}</option></select></label></article>)}</div></section>)}</div>
    </>
  )
}
