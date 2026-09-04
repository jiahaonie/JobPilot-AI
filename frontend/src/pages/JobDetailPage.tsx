import { useCallback, useState } from 'react'
import { ApiError } from '../api/client'
import { jobsApi } from '../api/jobs'
import { matchReportsApi } from '../api/matchReports'
import { resumesApi } from '../api/resumes'
import { AppLink, navigate } from '../app/router'
import { ErrorState, InlineMessage, LoadingState } from '../components/feedback/PageState'
import { SkillTags, StatusBadge } from '../components/ui/StatusBadge'
import { useAsyncResource } from '../hooks/useAsyncResource'
import { analysisStatusLabels, jobStatusLabels, type JobStatus } from '../types/api'

const nextStatuses: Partial<Record<JobStatus, JobStatus[]>> = {
  preparing: ['applied', 'closed'],
  applied: ['contacted', 'closed'],
  contacted: ['interview', 'closed'],
  interview: ['closed'],
}

export function JobDetailPage({ jobId }: { jobId: number }) {
  const loader = useCallback(async () => {
    const [job, resumes, reports] = await Promise.all([
      jobsApi.get(jobId), resumesApi.list(), matchReportsApi.list({ jobId }),
    ])
    let requirements = null
    try {
      requirements = await jobsApi.getRequirements(jobId)
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 404) throw error
    }
    return { job, resumes, reports, requirements }
  }, [jobId])
  const resource = useAsyncResource(loader)
  const [selectedResumeId, setSelectedResumeId] = useState('')
  const [busy, setBusy] = useState<string | null>(null)
  const [message, setMessage] = useState<{ kind: 'success' | 'error' | 'info'; text: string } | null>(null)

  async function run(label: string, action: () => Promise<unknown>, success: string) {
    setBusy(label)
    setMessage(null)
    try {
      await action()
      setMessage({ kind: 'success', text: success })
      resource.reload()
    } catch (error) {
      setMessage({ kind: 'error', text: error instanceof Error ? error.message : String(error) })
    } finally {
      setBusy(null)
    }
  }

  if (resource.loading) return <LoadingState label="正在读取岗位流程…" />
  if (resource.error) return <ErrorState error={resource.error} onRetry={resource.reload} />
  const { job, resumes, reports, requirements } = resource.data!
  const boundResume = resumes.find((resume) => resume.id === job.resume_id)
  const chosenResumeId = Number(selectedResumeId || job.resume_id || 0)
  const steps = [
    { label: '岗位已保存', done: true },
    { label: '绑定简历', done: Boolean(job.resume_id) },
    { label: '分析简历', done: boundResume?.analysis_status === 'ready' },
    { label: '分析 JD', done: job.analysis_status === 'ready' },
    { label: '保存报告', done: reports.length > 0 },
  ]

  async function createReport() {
    if (!job.resume_id) return
    setBusy('report')
    setMessage(null)
    try {
      const report = await jobsApi.createReport(job.id, job.resume_id)
      navigate(`/match-reports/${report.id}`)
    } catch (error) {
      setMessage({ kind: 'error', text: error instanceof Error ? error.message : String(error) })
      setBusy(null)
    }
  }

  return (
    <>
      <div className="page-heading">
        <div><p className="eyebrow">{job.company_name} · 岗位 #{job.id}</p><h1>{job.job_title}</h1><p>{job.city || '城市未填写'}{job.internship_duration ? ` · ${job.internship_duration}` : ''}</p></div>
        <StatusBadge status={job.status} />
      </div>
      {message && <InlineMessage kind={message.kind}>{message.text}</InlineMessage>}

      <ol className="workflow-steps" aria-label="岗位准备进度">
        {steps.map((step, index) => <li className={step.done ? 'done' : ''} key={step.label}><span>{step.done ? '✓' : index + 1}</span>{step.label}</li>)}
      </ol>

      <div className="detail-layout">
        <div className="detail-main">
          <section className="panel">
            <div className="section-heading"><div><p className="eyebrow">步骤 1</p><h2>绑定唯一简历</h2></div>{boundResume && <StatusBadge status={boundResume.analysis_status} />}</div>
            <p className="muted">投递准备开始后，不能再更换或解除绑定。</p>
            <div className="inline-controls">
              <select aria-label="选择简历" value={selectedResumeId || String(job.resume_id ?? '')} onChange={(event) => setSelectedResumeId(event.target.value)} disabled={job.status !== null}>
                <option value="">请选择简历</option>
                {[...resumes].sort((a, b) => Number(b.analysis_status === 'ready') - Number(a.analysis_status === 'ready')).map((resume) => <option value={resume.id} key={resume.id}>{resume.title}（{analysisStatusLabels[resume.analysis_status]}）</option>)}
              </select>
              <button className="button primary" disabled={!chosenResumeId || job.status !== null || busy !== null} onClick={() => run('bind', () => jobsApi.bindResume(job.id, chosenResumeId), '简历已绑定')}>{busy === 'bind' ? '绑定中…' : job.resume_id ? '更换绑定' : '绑定简历'}</button>
              {job.resume_id && job.status === null && <button className="button secondary" disabled={busy !== null} onClick={() => run('unbind', () => jobsApi.unbindResume(job.id), '已解除绑定')}>解除</button>}
            </div>
            {boundResume && <div className="sub-card"><strong>{boundResume.title}</strong><SkillTags skills={boundResume.skills} empty="尚未提取技能" />{boundResume.analysis_status !== 'ready' && <button className="button secondary" disabled={busy !== null} onClick={() => run('resume-analysis', () => resumesApi.analyze(boundResume.id), '简历技能分析已完成')}>{busy === 'resume-analysis' ? 'AI 正在分析，请勿重复提交…' : boundResume.analysis_status === 'failed' ? '重试简历分析' : '分析简历技能'}</button>}{boundResume.analysis_error && <p className="field-error">{boundResume.analysis_error}</p>}</div>}
          </section>

          <section className="panel">
            <div className="section-heading"><div><p className="eyebrow">步骤 2</p><h2>岗位 JD 分析</h2></div><StatusBadge status={job.analysis_status} /></div>
            <p className="muted">读取页面不会调用 LLM；只有点击分析按钮才会覆盖最新结果。</p>
            <button className="button primary" disabled={busy !== null} onClick={() => run('job-analysis', () => jobsApi.analyze(job.id), '岗位要求分析已完成')}>{busy === 'job-analysis' ? 'AI 正在分析，请勿重复提交…' : requirements ? '重新分析 JD' : '开始分析 JD'}</button>
            {job.analysis_error && <p className="field-error">{job.analysis_error}</p>}
            {requirements && <div className="requirements"><div><h3>必需技能</h3><SkillTags skills={requirements.required_skills} /></div><div><h3>加分技能</h3><SkillTags skills={requirements.preferred_skills} /></div><div><h3>主要职责</h3>{requirements.responsibilities.length ? <ul>{requirements.responsibilities.map((item) => <li key={item}>{item}</li>)}</ul> : <p className="muted">暂无</p>}</div></div>}
          </section>

          <section className="panel">
            <div className="section-heading"><div><p className="eyebrow">步骤 3</p><h2>保存匹配报告</h2></div><span className="count-pill">{reports.length} 份历史报告</span></div>
            <p className="muted">报告保存岗位要求与简历技能快照，刷新后仍可查看。</p>
            <button className="button primary" disabled={!job.resume_id || job.analysis_status !== 'ready' || boundResume?.analysis_status !== 'ready' || busy !== null} onClick={createReport}>{busy === 'report' ? '正在生成…' : '生成并保存报告'}</button>
            {!!reports.length && <div className="report-links">{reports.slice(-3).reverse().map((report) => <AppLink to={`/match-reports/${report.id}`} key={report.id}>报告 #{report.id} · {report.skill_coverage_score === null ? '不可评分' : `${Math.round(report.skill_coverage_score)}%`}</AppLink>)}</div>}
          </section>
        </div>

        <aside className="detail-side">
          <section className="panel sticky-panel"><p className="eyebrow">投递流程</p><h2>{job.status ? jobStatusLabels[job.status] : '尚未开始准备'}</h2>
            {!job.status ? <button className="button primary full" disabled={!job.resume_id || job.analysis_status !== 'ready' || boundResume?.analysis_status !== 'ready' || busy !== null} onClick={() => run('prepare', () => jobsApi.prepare(job.id), '投递准备已开始')}>开始投递准备</button> : <div className="status-actions">{(nextStatuses[job.status] ?? []).map((status) => <button className={status === 'closed' ? 'button danger-ghost full' : 'button secondary full'} disabled={busy !== null} key={status} onClick={() => run(`status-${status}`, () => jobsApi.updateStatus(job.id, status), `状态已更新为${jobStatusLabels[status]}`)}>更新为{jobStatusLabels[status]}</button>)}</div>}
            <div className="divider" />
            <h3>岗位原文</h3><p className="raw-preview">{job.raw_text}</p>
            {job.source_url && <a href={job.source_url} target="_blank" rel="noreferrer">打开来源链接 ↗</a>}
          </section>
        </aside>
      </div>
    </>
  )
}
