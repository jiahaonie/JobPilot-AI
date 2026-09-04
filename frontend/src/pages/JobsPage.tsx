import { useCallback, useState } from 'react'
import { jobsApi } from '../api/jobs'
import { AppLink, navigate } from '../app/router'
import { EmptyState, ErrorState, InlineMessage, LoadingState } from '../components/feedback/PageState'
import { StatusBadge } from '../components/ui/StatusBadge'
import { useAsyncResource } from '../hooks/useAsyncResource'
import { formatDate } from '../utils/format'

export function JobsPage() {
  const loader = useCallback(() => jobsApi.list(), [])
  const resource = useAsyncResource(loader)

  async function removeJob(id: number, label: string) {
    if (!window.confirm(`确定删除“${label}”吗？关联的要求、匹配报告和学习计划可能一并删除。`)) return
    try {
      await jobsApi.remove(id)
      resource.reload()
    } catch (error) {
      window.alert(error instanceof Error ? error.message : String(error))
    }
  }

  return (
    <>
      <div className="page-heading">
        <div><p className="eyebrow">机会管理</p><h1>岗位</h1><p>保存 JD，跟踪分析和投递状态。</p></div>
        <AppLink to="/jobs/new" className="button primary">创建岗位</AppLink>
      </div>
      {resource.loading ? <LoadingState /> : resource.error ? <ErrorState error={resource.error} onRetry={resource.reload} /> : !resource.data?.length ? (
        <EmptyState title="还没有岗位" description="创建第一个目标岗位，开始完整准备流程。" action={<AppLink to="/jobs/new" className="button primary">创建岗位</AppLink>} />
      ) : (
        <div className="card-grid">
          {resource.data.map((job) => (
            <article className="entity-card" key={job.id}>
              <div className="card-topline"><span>#{job.id}</span><StatusBadge status={job.status} /></div>
              <h2><AppLink to={`/jobs/${job.id}`}>{job.job_title}</AppLink></h2>
              <p>{job.company_name}{job.city ? ` · ${job.city}` : ''}</p>
              <dl className="compact-details">
                <div><dt>JD 分析</dt><dd><StatusBadge status={job.analysis_status} /></dd></div>
                <div><dt>绑定简历</dt><dd>{job.resume_id ? `#${job.resume_id}` : '未绑定'}</dd></div>
                <div><dt>创建时间</dt><dd>{formatDate(job.created_at, true)}</dd></div>
              </dl>
              <div className="card-actions"><AppLink to={`/jobs/${job.id}`} className="button secondary">打开流程</AppLink><button className="button danger-ghost" onClick={() => removeJob(job.id, job.job_title)}>删除</button></div>
            </article>
          ))}
        </div>
      )}
    </>
  )
}

export function NewJobPage() {
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [rawText, setRawText] = useState('')

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    const form = new FormData(event.currentTarget)
    try {
      const job = await jobsApi.create({
        company_name: String(form.get('company_name') ?? '').trim(),
        job_title: String(form.get('job_title') ?? '').trim(),
        city: String(form.get('city') ?? '').trim() || null,
        internship_duration: String(form.get('internship_duration') ?? '').trim() || null,
        raw_text: rawText.trim(),
        source_url: String(form.get('source_url') ?? '').trim() || null,
      })
      navigate(`/jobs/${job.id}`)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <div className="page-heading"><div><p className="eyebrow">新机会</p><h1>创建岗位</h1><p>这里只保存信息，不会自动调用 LLM。</p></div></div>
      <form className="panel form-panel" onSubmit={submit}>
        {error && <InlineMessage kind="error">{error}</InlineMessage>}
        <div className="form-grid">
          <label><span>公司名称 *</span><input name="company_name" required maxLength={200} /></label>
          <label><span>岗位名称 *</span><input name="job_title" required maxLength={200} /></label>
          <label><span>城市</span><input name="city" maxLength={100} /></label>
          <label><span>实习时长</span><input name="internship_duration" maxLength={100} placeholder="例如：3 个月" /></label>
          <label className="full-width"><span>来源链接</span><input name="source_url" type="url" maxLength={1000} /></label>
          <label className="full-width"><span>岗位描述 JD * <small>{rawText.length.toLocaleString()}/100,000</small></span><textarea required maxLength={100000} rows={14} value={rawText} onChange={(event) => setRawText(event.target.value)} /></label>
        </div>
        <div className="form-actions"><AppLink to="/jobs" className="button secondary">取消</AppLink><button className="button primary" disabled={submitting}>{submitting ? '正在保存…' : '保存并继续'}</button></div>
      </form>
    </>
  )
}
