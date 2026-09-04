import { useCallback, useState } from 'react'
import { resumesApi } from '../api/resumes'
import { AppLink, navigate } from '../app/router'
import { ErrorState, InlineMessage, LoadingState } from '../components/feedback/PageState'
import { SkillTags, StatusBadge } from '../components/ui/StatusBadge'
import { useAsyncResource } from '../hooks/useAsyncResource'
import { formatDate } from '../utils/format'

export function ResumeDetailPage({ resumeId }: { resumeId: number }) {
  const loader = useCallback(() => resumesApi.get(resumeId), [resumeId])
  const resource = useAsyncResource(loader)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function analyze() {
    setBusy(true); setError(null)
    try { await resumesApi.analyze(resumeId); resource.reload() }
    catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)) }
    finally { setBusy(false) }
  }

  async function remove() {
    if (!window.confirm('确定删除这份简历吗？如果仍被岗位绑定，后端会拒绝删除。')) return
    setBusy(true); setError(null)
    try { await resumesApi.remove(resumeId); navigate('/resumes') }
    catch (reason) { setError(`${reason instanceof Error ? reason.message : String(reason)}。如简历正在使用，请先到对应岗位解除绑定。`) }
    finally { setBusy(false) }
  }

  if (resource.loading) return <LoadingState />
  if (resource.error) return <ErrorState error={resource.error} onRetry={resource.reload} />
  const resume = resource.data!
  return (
    <>
      <div className="page-heading"><div><p className="eyebrow">简历 #{resume.id}</p><h1>{resume.title}</h1><p>创建于 {formatDate(resume.created_at)}</p></div><StatusBadge status={resume.analysis_status} /></div>
      {error && <InlineMessage kind="error">{error}</InlineMessage>}
      <div className="detail-layout">
        <div className="detail-main">
          <section className="panel"><div className="section-heading"><div><p className="eyebrow">分析结果</p><h2>技能</h2></div></div><SkillTags skills={resume.skills} empty="尚未提取技能" />{resume.analysis_error && <p className="field-error">{resume.analysis_error}</p>}<div className="form-actions left"><button className="button primary" onClick={analyze} disabled={busy}>{busy ? 'AI 正在分析，请勿重复提交…' : resume.analysis_status === 'failed' ? '重试分析' : resume.analysis_status === 'ready' ? '重新分析' : '开始分析'}</button><AppLink to="/jobs" className="button secondary">去绑定岗位</AppLink></div></section>
          <section className="panel"><p className="eyebrow">原始内容</p><h2>简历原文</h2><pre className="document-text">{resume.raw_text}</pre></section>
        </div>
        <aside className="detail-side"><section className="panel"><h2>管理</h2><p className="muted">删除前请确认没有岗位绑定这份简历。</p><button className="button danger-ghost full" onClick={remove} disabled={busy}>删除简历</button></section></aside>
      </div>
    </>
  )
}
